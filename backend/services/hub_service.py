"""
Hub Service
Aggregates anomaly data from multiple terminal nodes,
runs cross-node correlation, and produces unified threat views.
"""
import uuid
import json
import platform
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any, Optional

from core.database import db
from models.node import QuorumNode, NodeRole, NodeStatus, SyncMethod, SyncPackage
from core.exceptions import DatabaseError
from config.settings import settings
from config.logging_config import get_logger

logger = get_logger(__name__)


class HubService:
    """
    Hub aggregation service.

    On a TERMINAL node: exports local results as a SyncPackage.
    On a HUB node:      imports packages from terminals, aggregates, correlates.
    """

    def __init__(self):
        self.this_node_id = self._get_or_create_node_id()

    # ─── Node Registration ───────────────────────────────────────────────────

    def register_this_node(self, role: str = 'terminal') -> QuorumNode:
        """Register or update this machine as a Quorum node"""
        import socket
        hostname = socket.gethostname()
        os_info  = f"{platform.system()} {platform.version()[:30]}"

        existing = db.fetch_one(
            "SELECT * FROM node_registry WHERE node_id = ?",
            (self.this_node_id,)
        )

        node = QuorumNode(
            node_id         = self.this_node_id,
            hostname        = hostname,
            role            = NodeRole(role),
            status          = NodeStatus.ACTIVE,
            ip_address      = self._get_local_ip(),
            os_info         = os_info,
            quorum_version  = settings.APP_VERSION,
            last_seen       = datetime.utcnow(),
            total_logs      = db.get_table_count('logs'),
            total_anomalies = db.get_table_count('anomalies'),
            sync_method     = SyncMethod.USB
        )

        if existing:
            db.execute("""
                UPDATE node_registry
                SET status=?, last_seen=?, ip_address=?,
                    total_logs=?, total_anomalies=?, quorum_version=?
                WHERE node_id=?
            """, (
                node.status.value, node.last_seen, node.ip_address,
                node.total_logs, node.total_anomalies, node.quorum_version,
                node.node_id
            ))
        else:
            db.insert_batch('node_registry', [node.to_dict()])

        logger.info(f"Node registered: {hostname} ({role})")
        return node

    def register_remote_node(self, node_data: Dict[str, Any]) -> QuorumNode:
        """Register a remote node received via sync package"""
        node = QuorumNode.from_dict(node_data)
        node.last_seen = datetime.utcnow()

        existing = db.fetch_one(
            "SELECT node_id FROM node_registry WHERE node_id = ?",
            (node.node_id,)
        )

        if existing:
            db.execute("""
                UPDATE node_registry
                SET hostname=?, status=?, last_seen=?,
                    total_logs=?, total_anomalies=?, ip_address=?
                WHERE node_id=?
            """, (
                node.hostname, NodeStatus.INACTIVE.value, node.last_seen,
                node.total_logs, node.total_anomalies, node.ip_address,
                node.node_id
            ))
        else:
            db.insert_batch('node_registry', [node.to_dict()])

        logger.info(f"Remote node registered: {node.hostname}")
        return node

    def list_nodes(self) -> List[Dict[str, Any]]:
        """List all known nodes"""
        return db.fetch_all(
            "SELECT * FROM node_registry ORDER BY last_seen DESC"
        )

    def get_node(self, node_id: str) -> Optional[Dict[str, Any]]:
        return db.fetch_one(
            "SELECT * FROM node_registry WHERE node_id = ?", (node_id,)
        )

    # ─── Sync Package Export (Terminal → Hub) ────────────────────────────────

    def export_sync_package(
        self,
        target_node_id: str = 'hub',
        output_path: Optional[Path] = None,
        sign: bool = True
    ) -> Path:
        """
        Export local anomalies + node info as a signed sync package.
        Save as .qsp (Quorum Sync Package) file.
        """
        logger.info("Creating sync package...")

        # Gather anomalies
        anomalies = db.fetch_all("""
            SELECT a.*, l.timestamp, l.source, l.event_type,
                   l.hostname, l.username, l.message
            FROM anomalies a
            JOIN logs l ON a.log_id = l.id
            ORDER BY a.anomaly_score DESC
            LIMIT 500
        """)

        # Node info
        node_data = {
            'node_id':        self.this_node_id,
            'hostname':       self._get_hostname(),
            'role':           'terminal',
            'total_logs':     db.get_table_count('logs'),
            'total_anomalies': db.get_table_count('anomalies'),
            'os_info':        f"{platform.system()} {platform.version()[:30]}",
            'quorum_version': settings.APP_VERSION,
            'ip_address':     self._get_local_ip(),
        }

        package = SyncPackage(
            package_id   = str(uuid.uuid4()),
            source_node  = self.this_node_id,
            target_node  = target_node_id,
            sync_method  = SyncMethod.USB,
            created_at   = datetime.utcnow(),
            anomalies    = [dict(a) for a in anomalies],
            logs_summary = node_data,
            metadata     = {'exported_at': datetime.utcnow().isoformat()}
        )

        # Default output path
        if not output_path:
            ts = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_path = settings.DATA_DIR / f"sync_{self.this_node_id[:8]}_{ts}.qsp"

        package_dict = package.to_dict()

        # Sign if requested
        if sign:
            try:
                import base64
                from core.security import CryptoUtils
                payload_bytes = json.dumps(package_dict).encode()
                with open(settings.KEYS_DIR / 'private_key.pem', 'rb') as f:
                    priv = f.read()
                sig = CryptoUtils.sign_data(priv, payload_bytes)
                package_dict['signature'] = base64.b64encode(sig).decode()
            except Exception as e:
                logger.warning(f"Signing failed (exporting unsigned): {e}")

        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(package_dict, f, indent=2, default=str)

        logger.info(f"Sync package exported: {output_path} ({len(anomalies)} anomalies)")
        return output_path

    # ─── Sync Package Import (Hub receives from Terminal) ────────────────────

    def import_sync_package(self, package_path: Path) -> Dict[str, Any]:
        """
        Import a sync package on the HUB node.
        Merges terminal anomalies into hub database with node attribution.
        """
        logger.info(f"Importing sync package: {package_path}")

        with open(package_path, 'r', encoding='utf-8') as f:
            package_dict = json.load(f)

        source_node = package_dict.get('source_node', 'unknown')
        anomalies   = package_dict.get('anomalies', [])
        node_info   = package_dict.get('logs_summary', {})

        # Register the source node
        if node_info:
            self.register_remote_node({**node_info, 'status': 'inactive'})

        # Merge anomalies with node attribution
        merged = 0
        for anomaly in anomalies:
            try:
                # Check if already imported
                existing = db.fetch_one(
                    "SELECT 1 AS exists_flag FROM hub_anomalies WHERE original_id=? AND source_node=?",
                    (anomaly.get('id'), source_node)
                )
                if existing:
                    continue

                db.execute("""
                    INSERT INTO hub_anomalies
                    (original_id, source_node, anomaly_score, severity,
                     algorithm, mitre_technique_id, mitre_tactic,
                     log_timestamp, source, event_type, message,
                     hostname, username, imported_at)
                    VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)
                """, (
                    anomaly.get('id'), source_node,
                    anomaly.get('anomaly_score', 0),
                    anomaly.get('severity', 'UNKNOWN'),
                    anomaly.get('algorithm', 'unknown'),
                    anomaly.get('mitre_technique_id'),
                    anomaly.get('mitre_tactic'),
                    anomaly.get('timestamp'),
                    anomaly.get('source'),
                    anomaly.get('event_type'),
                    (anomaly.get('message') or '')[:500],
                    anomaly.get('hostname'),
                    anomaly.get('username'),
                    datetime.utcnow()
                ))
                merged += 1
            except Exception as e:
                logger.debug(f"Anomaly merge error: {e}")

        # Log sync event
        db.execute("""
            INSERT INTO node_sync_log
            (sync_id, source_node, target_node, sync_method,
             anomalies_synced, synced_at, package_path)
            VALUES (?,?,?,?,?,?,?)
        """, (
            package_dict.get('package_id', str(uuid.uuid4())),
            source_node, self.this_node_id, 'usb',
            merged, datetime.utcnow(), str(package_path)
        ))

        # Update node stats
        db.execute("""
            UPDATE node_registry
            SET last_sync=?, total_anomalies=?
            WHERE node_id=?
        """, (datetime.utcnow(), node_info.get('total_anomalies', 0), source_node))

        logger.info(f"Imported {merged} anomalies from node {source_node}")
        return {
            'source_node':     source_node,
            'anomalies_merged': merged,
            'total_in_package': len(anomalies)
        }

    # ─── Aggregated Views ────────────────────────────────────────────────────

    def get_aggregated_dashboard(self) -> Dict[str, Any]:
        """Get hub-level aggregated threat overview across all nodes"""
        try:
            # Node summary
            nodes = db.fetch_all("SELECT * FROM node_registry ORDER BY last_seen DESC")

            # Aggregated anomaly counts by severity
            severity_dist = db.fetch_all("""
                SELECT severity, COUNT(*) as count
                FROM hub_anomalies
                GROUP BY severity
                ORDER BY count DESC
            """)

            # Aggregated MITRE tactic distribution
            mitre_dist = db.fetch_all("""
                SELECT mitre_tactic, COUNT(*) as count
                FROM hub_anomalies
                WHERE mitre_tactic IS NOT NULL
                GROUP BY mitre_tactic
                ORDER BY count DESC
            """)

            # Per-node threat summary
            node_threats = db.fetch_all("""
                SELECT source_node,
                       COUNT(*) as total_anomalies,
                       SUM(CASE WHEN severity='CRITICAL' THEN 1 ELSE 0 END) as critical,
                       SUM(CASE WHEN severity='HIGH' THEN 1 ELSE 0 END) as high,
                       AVG(anomaly_score) as avg_score,
                       MAX(imported_at) as last_sync
                FROM hub_anomalies
                GROUP BY source_node
            """)

            # Total counts
            total_anomalies = db.get_table_count('hub_anomalies')
            total_nodes     = len(nodes)

            return {
                'total_nodes':      total_nodes,
                'total_anomalies':  total_anomalies,
                'nodes':            nodes,
                'severity_dist':    {r['severity']: r['count'] for r in severity_dist},
                'mitre_dist':       mitre_dist,
                'node_threats':     node_threats,
                'generated_at':     datetime.utcnow().isoformat()
            }
        except Exception as e:
            logger.error(f"Dashboard error: {e}")
            return {}

    def get_cross_node_correlations(self) -> List[Dict[str, Any]]:
        """
        Find attack patterns that appear across multiple nodes.
        Same MITRE technique on 2+ nodes = correlated attack.
        """
        try:
            correlations = db.fetch_all("""
                SELECT
                    mitre_technique_id,
                    mitre_tactic,
                    COUNT(DISTINCT source_node)  as node_count,
                    COUNT(*)                     as total_hits,
                    GROUP_CONCAT(DISTINCT source_node) as affected_nodes,
                    AVG(anomaly_score)           as avg_score,
                    MIN(log_timestamp)           as first_seen,
                    MAX(log_timestamp)           as last_seen
                FROM hub_anomalies
                WHERE mitre_technique_id IS NOT NULL
                GROUP BY mitre_technique_id, mitre_tactic
                HAVING node_count >= 2
                ORDER BY node_count DESC, total_hits DESC
            """)

            results = []
            for c in correlations:
                threat_level = 'CRITICAL' if c['node_count'] >= 3 else 'HIGH'
                results.append({
                    **dict(c),
                    'threat_level': threat_level,
                    'is_coordinated': c['node_count'] >= 2
                })

            logger.info(f"Found {len(results)} cross-node correlations")
            return results

        except Exception as e:
            logger.error(f"Correlation error: {e}")
            return []

    def get_mitre_heatmap(self) -> Dict[str, Any]:
        """Get MITRE ATT&CK heatmap data (tactic × node)"""
        try:
            rows = db.fetch_all("""
                SELECT source_node, mitre_tactic, COUNT(*) as count
                FROM hub_anomalies
                WHERE mitre_tactic IS NOT NULL
                GROUP BY source_node, mitre_tactic
            """)

            nodes   = list({r['source_node'] for r in rows})
            tactics = list({r['mitre_tactic'] for r in rows})

            matrix = {node: {tactic: 0 for tactic in tactics} for node in nodes}
            for r in rows:
                matrix[r['source_node']][r['mitre_tactic']] = r['count']

            return {
                'nodes':   nodes,
                'tactics': tactics,
                'matrix':  matrix
            }
        except Exception as e:
            logger.error(f"Heatmap error: {e}")
            return {}

    def scan_usb_for_sync_packages(self) -> List[Path]:
        """Scan USB drives for .qsp sync packages"""
        from core.device_monitor import device_monitor
        packages = []

        usb_devices = device_monitor.enumerate_usb_devices()
        for device in usb_devices:
            if device.mount_point:
                try:
                    for qsp in Path(device.mount_point).rglob('*.qsp'):
                        packages.append(qsp)
                        logger.info(f"Found sync package: {qsp}")
                except Exception:
                    pass

        return packages

    # ─── Helpers ─────────────────────────────────────────────────────────────

    def _get_or_create_node_id(self) -> str:
        node_id_file = settings.DATA_DIR / 'node_id'
        if node_id_file.exists():
            return node_id_file.read_text().strip()
        new_id = str(uuid.uuid4())
        node_id_file.write_text(new_id)
        return new_id

    def _get_hostname(self) -> str:
        import socket
        return socket.gethostname()

    def _get_local_ip(self) -> Optional[str]:
        import socket
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect(('8.8.8.8', 80))
            ip = s.getsockname()[0]
            s.close()
            return ip
        except Exception:
            return None


# Global instance
hub_service = HubService()
