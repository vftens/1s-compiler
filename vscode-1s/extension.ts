/**
 * 1S: ERP Language Support — VS Code Extension
 * Provides: syntax highlighting, snippets, Run button (Ctrl+F5)
 */
import * as vscode from 'vscode';
import * as cp from 'child_process';
import * as path from 'path';

let outputChannel: vscode.OutputChannel;

export function activate(context: vscode.ExtensionContext) {
    outputChannel = vscode.window.createOutputChannel('1S: ERP');

    const runCmd = vscode.commands.registerCommand('1s-erp.runScript', () => {
        const editor = vscode.window.activeTextEditor;
        if (!editor) {
            vscode.window.showWarningMessage('No active .1s file');
            return;
        }
        const filePath = editor.document.fileName;
        if (!filePath.endsWith('.1s')) {
            vscode.window.showWarningMessage('Not a .1s file');
            return;
        }

        const config     = vscode.workspace.getConfiguration('1s-erp');
        const python     = config.get<string>('pythonPath', 'python');
        const projectRoot = config.get<string>('projectRoot', '')
                            || findProjectRoot(filePath)
                            || path.dirname(filePath);

        outputChannel.clear();
        outputChannel.show(true);
        outputChannel.appendLine(`▶ Running: ${path.basename(filePath)}`);
        outputChannel.appendLine(`  Project: ${projectRoot}\n`);

        const env = { ...process.env, PYTHONUTF8: '1', PYTHONPATH: projectRoot };
        const proc = cp.spawn(python, ['-m', 'src.cli', 'run', filePath], {
            cwd: projectRoot, env,
        });

        proc.stdout.on('data', (d: Buffer) =>
            outputChannel.append(d.toString('utf8')));
        proc.stderr.on('data', (d: Buffer) =>
            outputChannel.append(d.toString('utf8')));
        proc.on('close', (code: number) => {
            outputChannel.appendLine(`\n── Exit code: ${code} ──`);
        });
    });

    context.subscriptions.push(runCmd);
}

function findProjectRoot(filePath: string): string | null {
    let dir = path.dirname(filePath);
    for (let i = 0; i < 10; i++) {
        const candidate = path.join(dir, 'src', 'cli.py');
        if (require('fs').existsSync(candidate)) return dir;
        const parent = path.dirname(dir);
        if (parent === dir) break;
        dir = parent;
    }
    return null;
}

export function deactivate() {}
