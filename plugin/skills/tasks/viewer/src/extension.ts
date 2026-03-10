import * as vscode from 'vscode';
import * as path from 'path';
import * as fs from 'fs';
import { BacklogViewProvider } from './backlog-view';
import { TaskDetailPanel } from './task-detail-panel';

export const activate = (context: vscode.ExtensionContext): void => {
  const tasksDir = findTasksDir();
  if (!tasksDir) return;

  const provider = new BacklogViewProvider(tasksDir);

  context.subscriptions.push(
    vscode.window.registerWebviewViewProvider('tasksBacklog', provider),
    vscode.commands.registerCommand('tasksViewer.refresh', () => provider.refresh()),
    vscode.window.registerWebviewPanelSerializer('taskDetail', {
      deserializeWebviewPanel: (panel: vscode.WebviewPanel, state: { readonly tasksDir: string; readonly taskRelPath: string }) => {
        if (state?.tasksDir && state?.taskRelPath) {
          TaskDetailPanel.restore(panel, state.tasksDir, state.taskRelPath);
        } else {
          panel.dispose();
        }
        return Promise.resolve();
      },
    }),
  );

  // Watch .tasks/ for changes with debounce
  const pattern = new vscode.RelativePattern(vscode.Uri.file(tasksDir), '**/*');
  const watcher = vscode.workspace.createFileSystemWatcher(pattern);
  let debounceTimer: ReturnType<typeof setTimeout> | undefined;
  const debouncedRefresh = (): void => {
    if (debounceTimer) clearTimeout(debounceTimer);
    debounceTimer = setTimeout(() => {
      provider.refresh();
      TaskDetailPanel.refreshAll();
    }, 300);
  };
  watcher.onDidChange(debouncedRefresh);
  watcher.onDidCreate(debouncedRefresh);
  watcher.onDidDelete(debouncedRefresh);
  context.subscriptions.push(watcher);
};

const findTasksDir = (): string | undefined => {
  const folders = vscode.workspace.workspaceFolders ?? [];
  const match = folders.find(folder =>
    fs.existsSync(path.join(folder.uri.fsPath, '.tasks', 'INDEX.md'))
  );
  return match ? path.join(match.uri.fsPath, '.tasks') : undefined;
};

export const deactivate = (): void => {};
