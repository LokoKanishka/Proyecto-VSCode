import * as vscode from 'vscode';
import { WebSocketServer } from 'ws';

interface CommandMessage {
  type: 'command';
  action: string;
  args?: Record<string, any>;
}

let wss: WebSocketServer | null = null;

export function activate(context: vscode.ExtensionContext) {
  wss = new WebSocketServer({ port: 8765 });

  wss.on('connection', (socket) => {
    socket.on('message', async (raw) => {
      try {
        const data = JSON.parse(raw.toString()) as CommandMessage;
        if (data.type !== 'command') {
          socket.send(JSON.stringify({ type: 'error', error: 'Invalid message type' }));
          return;
        }
        const result = await handleCommand(data.action, data.args || {});
        socket.send(JSON.stringify({ type: 'response', status: 'success', result }));
      } catch (err: any) {
        socket.send(JSON.stringify({ type: 'error', error: err?.message || 'Unknown error' }));
      }
    });
  });

  context.subscriptions.push({
    dispose: () => {
      wss?.close();
      wss = null;
    },
  });
}

async function handleCommand(action: string, args: Record<string, any>) {
  switch (action) {
    case 'openFile':
      return openFile(args.path, args.line, args.column);
    case 'insertText':
      return insertText(args.text);
    case 'saveFile':
      return saveActiveFile();
    case 'runCommand':
      return vscode.commands.executeCommand(args.command, ...(args.params || []));
    default:
      throw new Error(`Unknown action: ${action}`);
  }
}

async function openFile(path?: string, line?: number, column?: number) {
  if (!path) {
    throw new Error('path required');
  }
  const doc = await vscode.workspace.openTextDocument(path);
  const editor = await vscode.window.showTextDocument(doc);
  if (line) {
    const pos = new vscode.Position(Math.max(0, line - 1), Math.max(0, (column || 1) - 1));
    editor.selection = new vscode.Selection(pos, pos);
    editor.revealRange(new vscode.Range(pos, pos));
  }
  return { opened: path };
}

async function insertText(text?: string) {
  if (!text) {
    throw new Error('text required');
  }
  const editor = vscode.window.activeTextEditor;
  if (!editor) {
    throw new Error('No active editor');
  }
  await editor.edit((editBuilder) => {
    editBuilder.insert(editor.selection.active, text);
  });
  return { inserted: text.length };
}

async function saveActiveFile() {
  const editor = vscode.window.activeTextEditor;
  if (!editor) {
    throw new Error('No active editor');
  }
  await editor.document.save();
  return { saved: editor.document.fileName };
}

export function deactivate() {
  wss?.close();
  wss = null;
}
