import { apiClient } from "./api";

export interface CommandRequest {
  command: string;
  args?: string[];
}

export interface CommandResponse {
  command: string;
  output: string;
  error?: string;
  exit_code: number;
  executed_at: string;
}

export interface CommandDocumentation {
  command: string;
  description: string;
  usage: string;
  examples: string[];
  category: string;
}

export interface CLIHelpResponse {
  title: string;
  version: string;
  description: string;
  getting_started: string[];
  categories: string[];
  total_commands: number;
}

class CLIService {
  /**
   * Get all CLI commands organized by category
   */
  async getAllCommands(): Promise<Record<string, CommandDocumentation[]>> {
    const response = await apiClient.get("/cli/commands");
    return response.data;
  }

  /**
   * Get CLI commands for a specific category
   */
  async getCommandsByCategory(category: string): Promise<CommandDocumentation[]> {
    const response = await apiClient.get(`/cli/commands/${category}`);
    return response.data;
  }

  /**
   * Execute a CLI command
   */
  async executeCommand(request: CommandRequest): Promise<CommandResponse> {
    const response = await apiClient.post("/cli/execute", request);
    return response.data;
  }

  /**
   * Get CLI help information
   */
  async getHelp(): Promise<CLIHelpResponse> {
    const response = await apiClient.get("/cli/help");
    return response.data;
  }
}

export const cliService = new CLIService();
