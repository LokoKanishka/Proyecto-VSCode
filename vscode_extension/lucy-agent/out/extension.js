"use strict";
var __createBinding = (this && this.__createBinding) || (Object.create ? (function(o, m, k, k2) {
    if (k2 === undefined) k2 = k;
    var desc = Object.getOwnPropertyDescriptor(m, k);
    if (!desc || ("get" in desc ? !m.__esModule : desc.writable || desc.configurable)) {
      desc = { enumerable: true, get: function() { return m[k]; } };
    }
    Object.defineProperty(o, k2, desc);
}) : (function(o, m, k, k2) {
    if (k2 === undefined) k2 = k;
    o[k2] = m[k];
}));
var __setModuleDefault = (this && this.__setModuleDefault) || (Object.create ? (function(o, v) {
    Object.defineProperty(o, "default", { enumerable: true, value: v });
}) : function(o, v) {
    o["default"] = v;
});
var __importStar = (this && this.__importStar) || (function () {
    var ownKeys = function(o) {
        ownKeys = Object.getOwnPropertyNames || function (o) {
            var ar = [];
            for (var k in o) if (Object.prototype.hasOwnProperty.call(o, k)) ar[ar.length] = k;
            return ar;
        };
        return ownKeys(o);
    };
    return function (mod) {
        if (mod && mod.__esModule) return mod;
        var result = {};
        if (mod != null) for (var k = ownKeys(mod), i = 0; i < k.length; i++) if (k[i] !== "default") __createBinding(result, mod, k[i]);
        __setModuleDefault(result, mod);
        return result;
    };
})();
Object.defineProperty(exports, "__esModule", { value: true });
exports.activate = activate;
exports.deactivate = deactivate;
const vscode = __importStar(require("vscode"));
const ws_1 = require("ws");
let wss = null;
function activate(context) {
    wss = new ws_1.WebSocketServer({ port: 8765 });
    wss.on('connection', (socket) => {
        socket.on('message', async (raw) => {
            try {
                const data = JSON.parse(raw.toString());
                if (data.type !== 'command') {
                    socket.send(JSON.stringify({ type: 'error', error: 'Invalid message type' }));
                    return;
                }
                const result = await handleCommand(data.action, data.args || {});
                socket.send(JSON.stringify({ type: 'response', status: 'success', result }));
            }
            catch (err) {
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
async function handleCommand(action, args) {
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
async function openFile(path, line, column) {
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
async function insertText(text) {
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
function deactivate() {
    wss?.close();
    wss = null;
}
//# sourceMappingURL=extension.js.map