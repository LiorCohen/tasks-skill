import * as vscode from 'vscode';
import * as fs from 'fs';
import * as path from 'path';
import MarkdownIt from 'markdown-it';
import hljs from 'highlight.js';

const PRIORITY_LABELS: Readonly<Record<string, string>> = {
  'high': '\u{1F534} High',
  'medium': '\u{1F7E1} Medium',
  'low': '\u{1F535} Low',
};

const STATUS_LABELS: Readonly<Record<string, string>> = {
  'inbox': '\u{1F4E5} Inbox',
  'speccing': '\u{1F4DD} Speccing',
  'planning': '\u{1F4D0} Planning',
  'plan-review': '\u2705 Plan Review',
  'implementing': '\u{1F528} Implementing',
  'reviewing': '\u{1F50D} Reviewing',
  'complete': '\u{1F389} Complete',
};

type TaskType = 'epic' | 'change';

type TaskFrontmatter = {
  readonly id?: string;
  readonly title?: string;
  readonly type?: TaskType;
  readonly status?: string;
  readonly priority?: string;
  readonly parentEpic?: string;
  readonly created?: string;
};

const md = new MarkdownIt({
  html: false,
  linkify: true,
  typographer: true,
  highlight: (str: string, lang: string): string => {
    if (lang && hljs.getLanguage(lang)) {
      return hljs.highlight(str, { language: lang }).value;
    }
    return hljs.highlightAuto(str).value;
  },
});

const OPEN_ICON = '<svg width="14" height="14" viewBox="0 0 16 16" fill="currentColor"><path d="M1.5 1h6v1H2v12h12V8.5h1v6a.5.5 0 0 1-.5.5h-13a.5.5 0 0 1-.5-.5v-13a.5.5 0 0 1 .5-.5z"/><path d="M15 1.5V7h-1V2.707L8.354 8.354l-.708-.708L13.293 2H9V1h5.5a.5.5 0 0 1 .5.5z"/></svg>';

export class TaskDetailPanel {
  private static panels = new Map<string, TaskDetailPanel>();

  private constructor(
    private readonly panel: vscode.WebviewPanel,
    private readonly tasksDir: string,
    private readonly taskId: string,
  ) {
    this.panel.onDidDispose(() => {
      TaskDetailPanel.panels.delete(taskId);
    });

    this.panel.iconPath = {
      light: vscode.Uri.file(path.join(__dirname, '..', 'media', 'icons', 'task-detail-light.svg')),
      dark: vscode.Uri.file(path.join(__dirname, '..', 'media', 'icons', 'task-detail-dark.svg')),
    };
    this.panel.webview.options = { enableScripts: true };
    this.panel.webview.onDidReceiveMessage((msg: { readonly command: string; readonly path?: string }) => {
      if (msg.command === 'openFile' && msg.path) {
        const fullPath = path.join(this.tasksDir, msg.path);
        if (fs.existsSync(fullPath)) {
          void vscode.window.showTextDocument(vscode.Uri.file(fullPath));
        }
      }
    });

    this.update();
  }

  static refreshAll(): void {
    for (const instance of TaskDetailPanel.panels.values()) {
      instance.update();
    }
  }

  static restore(panel: vscode.WebviewPanel, tasksDir: string, taskId: string): void {
    TaskDetailPanel.panels.set(taskId, new TaskDetailPanel(panel, tasksDir, taskId));
  }

  static show(tasksDir: string, taskRelPath: string): void {
    const taskDir = path.dirname(taskRelPath);
    const taskId = path.basename(taskDir);

    const existing = TaskDetailPanel.panels.get(taskId);
    if (existing) {
      existing.panel.reveal();
      existing.update();
      return;
    }

    const panel = vscode.window.createWebviewPanel(
      'taskDetail',
      `Task #${taskId}`,
      vscode.ViewColumn.One,
      { enableScripts: true, retainContextWhenHidden: true },
    );

    TaskDetailPanel.panels.set(taskId, new TaskDetailPanel(panel, tasksDir, taskId));
  }

  /** Find the task directory by scanning status dirs for the task ID. */
  private findTaskDir(): string | null {
    const statusDirs = [
      '0-inbox', '1-speccing', '2-planning', '3-plan-review',
      '4-implementing', '5-reviewing', '6-complete', '7-rejected', '8-consolidated',
    ];
    for (const dir of statusDirs) {
      const candidate = path.join(this.tasksDir, 'items', dir, this.taskId);
      if (fs.existsSync(candidate)) {
        return candidate;
      }
    }
    return null;
  }

  private update(): void {
    this.panel.webview.html = this.getHtml();
  }

  private getHtml(): string {
    const taskDir = this.findTaskDir();
    if (!taskDir) {
      return `<!DOCTYPE html><html><body><p>Task #${escapeHtml(this.taskId)} not found.</p></body></html>`;
    }

    // Read metadata from task.yaml (new) or task.md frontmatter (legacy)
    const yamlPath = path.join(taskDir, 'task.yaml');
    const legacyMdPath = path.join(taskDir, 'task.md');
    const specPath = path.join(taskDir, 'spec.md');
    const planPath = path.join(taskDir, 'plan.md');
    const implPath = path.join(taskDir, 'impl.md');
    const revwPath = path.join(taskDir, 'revw.md');
    // Legacy fallback
    const changesPath = path.join(taskDir, 'changes.md');

    let frontmatter: TaskFrontmatter;
    let specBody: string;

    if (fs.existsSync(yamlPath)) {
      // New format: task.yaml + spec.md
      frontmatter = parseYamlMeta(safeRead(yamlPath));
      specBody = fs.existsSync(specPath) ? parseFrontmatterAndBody(safeRead(specPath)).body : '';
    } else {
      // Legacy: task.md with frontmatter
      const parsed = parseFrontmatterAndBody(safeRead(legacyMdPath));
      frontmatter = parsed.frontmatter;
      specBody = parsed.body;
    }

    const id = frontmatter.id ?? path.basename(taskDir);
    const title = frontmatter.title ?? 'Untitled Task';
    const taskType = frontmatter.type ?? 'change';
    const status = frontmatter.status ?? 'unknown';
    const statusLabel = STATUS_LABELS[status] ?? status;
    const priority = frontmatter.priority;
    const priorityLabel = priority ? (PRIORITY_LABELS[priority] ?? priority) : '\u26AA None';
    const parentEpic = frontmatter.parentEpic;
    const created = frontmatter.created ?? '';

    const hasPlan = fs.existsSync(planPath);
    const hasImpl = fs.existsSync(implPath);
    const hasRevw = fs.existsSync(revwPath);
    const hasLegacyChanges = fs.existsSync(changesPath) && !hasRevw;

    const specRelPath = path.relative(this.tasksDir, specPath).replace(/\\/g, '/');
    const planRelPath = path.relative(this.tasksDir, planPath).replace(/\\/g, '/');
    const implRelPath = path.relative(this.tasksDir, implPath).replace(/\\/g, '/');
    const revwRelPath = path.relative(this.tasksDir, revwPath).replace(/\\/g, '/');
    const changesRelPath = path.relative(this.tasksDir, changesPath).replace(/\\/g, '/');

    const planRendered = hasPlan
      ? md.render(parseFrontmatterAndBody(safeRead(planPath)).body)
      : '';

    const implRendered = hasImpl
      ? md.render(parseFrontmatterAndBody(safeRead(implPath)).body)
      : '';

    const revwRendered = hasRevw
      ? md.render(parseFrontmatterAndBody(safeRead(revwPath)).body)
      : '';

    const changesRendered = hasLegacyChanges
      ? md.render(parseFrontmatterAndBody(safeRead(changesPath)).body)
      : '';

    return `<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<style>
  body {
    font-family: var(--vscode-font-family);
    font-size: var(--vscode-font-size);
    color: var(--vscode-foreground);
    background: var(--vscode-editor-background);
    padding: 24px 32px;
    margin: 0;
    max-width: 900px;
  }
  .header {
    margin-bottom: 20px;
    padding-bottom: 16px;
    border-bottom: 2px solid var(--vscode-panel-border);
  }
  .header h1 {
    margin: 0 0 8px;
    font-size: 1.5em;
    font-weight: 600;
  }
  .header h1 .task-num {
    color: var(--vscode-descriptionForeground);
    font-weight: 400;
  }
  .meta {
    display: flex;
    gap: 20px;
    flex-wrap: wrap;
    font-size: 0.9em;
  }
  .meta-item {
    display: flex;
    gap: 6px;
  }
  .meta-label {
    color: var(--vscode-descriptionForeground);
  }
  .tabs {
    display: flex;
    gap: 0;
    margin-top: 16px;
    border-bottom: 1px solid var(--vscode-panel-border);
  }
  .tab {
    display: flex;
    align-items: center;
    gap: 6px;
    padding: 6px 14px;
    cursor: pointer;
    font-size: 0.9em;
    font-family: var(--vscode-font-family);
    color: var(--vscode-descriptionForeground);
    background: none;
    border: none;
    border-bottom: 2px solid transparent;
    margin-bottom: -1px;
  }
  .tab:hover {
    color: var(--vscode-foreground);
  }
  .tab.active {
    color: var(--vscode-foreground);
    border-bottom-color: var(--vscode-focusBorder);
  }
  .tab-open-icon {
    display: inline-flex;
    align-items: center;
    padding: 2px;
    border-radius: 3px;
    cursor: pointer;
    color: var(--vscode-descriptionForeground);
    opacity: 0;
    transition: opacity 0.15s;
  }
  .tab:hover .tab-open-icon,
  .tab.active .tab-open-icon {
    opacity: 1;
  }
  .tab-open-icon:hover {
    color: var(--vscode-foreground);
    background: var(--vscode-toolbar-hoverBackground, rgba(128,128,128,0.2));
  }
  .tab-content {
    display: none;
    margin-top: 16px;
  }
  .tab-content.active {
    display: block;
  }
  .content {
    font-size: 0.92em;
    line-height: 1.6;
    color: var(--vscode-editor-foreground);
    overflow-x: auto;
  }
  .rendered-md h1, .rendered-md h2, .rendered-md h3 {
    margin: 16px 0 8px;
    font-weight: 600;
    border-bottom: 1px solid var(--vscode-panel-border);
    padding-bottom: 4px;
  }
  .rendered-md h1 { font-size: 1.3em; }
  .rendered-md h2 { font-size: 1.15em; }
  .rendered-md h3 { font-size: 1em; border: none; }
  .rendered-md p { margin: 8px 0; }
  .rendered-md ul, .rendered-md ol { padding-left: 24px; margin: 8px 0; }
  .rendered-md li { margin: 4px 0; }
  .rendered-md code {
    font-family: var(--vscode-editor-font-family, monospace);
    background: var(--vscode-textCodeBlock-background, rgba(128,128,128,0.15));
    padding: 2px 5px;
    border-radius: 3px;
    font-size: 0.9em;
  }
  .rendered-md pre {
    background: var(--vscode-textCodeBlock-background, rgba(128,128,128,0.15));
    padding: 12px 16px;
    border-radius: 4px;
    overflow-x: auto;
    margin: 12px 0;
  }
  .rendered-md pre code {
    background: none;
    padding: 0;
  }
  .rendered-md table {
    border-collapse: collapse;
    width: 100%;
    margin: 12px 0;
  }
  .rendered-md th, .rendered-md td {
    border: 1px solid var(--vscode-panel-border);
    padding: 6px 10px;
    text-align: left;
  }
  .rendered-md th {
    background: var(--vscode-textCodeBlock-background, rgba(128,128,128,0.1));
    font-weight: 600;
  }
  .rendered-md blockquote {
    border-left: 3px solid var(--vscode-textBlockQuote-border, var(--vscode-panel-border));
    margin: 12px 0;
    padding: 4px 16px;
    color: var(--vscode-descriptionForeground);
  }
  .rendered-md a {
    color: var(--vscode-textLink-foreground);
    text-decoration: none;
  }
  .rendered-md a:hover {
    text-decoration: underline;
  }
  .epic-badge {
    font-size: 0.8em;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 0.3px;
    color: var(--vscode-editorInfo-foreground, #3794ff);
    background: rgba(55, 148, 255, 0.15);
    padding: 1px 6px;
    border-radius: 3px;
  }
  /* highlight.js tokens mapped to VS Code theme */
  .hljs-keyword, .hljs-selector-tag, .hljs-built_in, .hljs-name { color: var(--vscode-symbolIcon-keywordForeground, #569cd6); }
  .hljs-string, .hljs-attr, .hljs-template-tag { color: var(--vscode-symbolIcon-stringForeground, #ce9178); }
  .hljs-number, .hljs-literal, .hljs-variable.constant_ { color: var(--vscode-symbolIcon-numberForeground, #b5cea8); }
  .hljs-comment, .hljs-doctag { color: var(--vscode-symbolIcon-commentForeground, #6a9955); font-style: italic; }
  .hljs-type, .hljs-class .hljs-title, .hljs-title.class_ { color: var(--vscode-symbolIcon-classForeground, #4ec9b0); }
  .hljs-function .hljs-title, .hljs-title.function_ { color: var(--vscode-symbolIcon-functionForeground, #dcdcaa); }
  .hljs-regexp, .hljs-meta { color: var(--vscode-symbolIcon-referenceForeground, #d16969); }
  .hljs-params { color: var(--vscode-symbolIcon-parameterForeground, #9cdcfe); }
  .hljs-property { color: var(--vscode-symbolIcon-propertyForeground, #9cdcfe); }
  .hljs-tag { color: var(--vscode-symbolIcon-colorForeground, #569cd6); }
  .hljs-attr { color: var(--vscode-symbolIcon-propertyForeground, #9cdcfe); }
  .hljs-selector-class, .hljs-selector-id { color: var(--vscode-symbolIcon-classForeground, #d7ba7d); }
  .hljs-punctuation { color: var(--vscode-editorBracketHighlight-foreground1, #d4d4d4); }
  .hljs-operator { color: var(--vscode-editorBracketHighlight-foreground2, #d4d4d4); }
  .hljs-section { color: var(--vscode-symbolIcon-functionForeground, #dcdcaa); font-weight: bold; }
  .hljs-deletion { color: var(--vscode-gitDecoration-deletedResourceForeground, #ce9178); background: rgba(255,0,0,0.1); }
  .hljs-addition { color: var(--vscode-gitDecoration-addedResourceForeground, #b5cea8); background: rgba(0,255,0,0.1); }
</style>
</head>
<body>
  <div class="header">
    <h1><span class="task-num">#${escapeHtml(id)}</span> ${escapeHtml(title)}</h1>
    <div class="meta">
      <div class="meta-item"><span class="meta-label">Status:</span> ${statusLabel}</div>
      ${taskType === 'epic' ? '<div class="meta-item"><span class="meta-label">Type:</span> <span class="epic-badge">Epic</span></div>' : ''}
      ${parentEpic ? `<div class="meta-item"><span class="meta-label">Epic:</span> #${escapeHtml(parentEpic)}</div>` : ''}
      <div class="meta-item">
        <span class="meta-label">Priority:</span>
        <span class="priority-display">${priorityLabel}</span>
      </div>
      ${created ? `<div class="meta-item"><span class="meta-label">Created:</span> ${escapeHtml(created)}</div>` : ''}
    </div>
    <div class="tabs">
      <button class="tab active" data-tab="spec">spec.md <span class="tab-open-icon" data-path="${escapeHtml(specRelPath)}" title="Open in editor">${OPEN_ICON}</span></button>
      ${hasPlan ? `<button class="tab" data-tab="plan">plan.md <span class="tab-open-icon" data-path="${escapeHtml(planRelPath)}" title="Open in editor">${OPEN_ICON}</span></button>` : ''}
      ${hasImpl ? `<button class="tab" data-tab="impl">impl.md <span class="tab-open-icon" data-path="${escapeHtml(implRelPath)}" title="Open in editor">${OPEN_ICON}</span></button>` : ''}
      ${hasRevw ? `<button class="tab" data-tab="revw">revw.md <span class="tab-open-icon" data-path="${escapeHtml(revwRelPath)}" title="Open in editor">${OPEN_ICON}</span></button>` : ''}
      ${hasLegacyChanges ? `<button class="tab" data-tab="changes">changes.md <span class="tab-open-icon" data-path="${escapeHtml(changesRelPath)}" title="Open in editor">${OPEN_ICON}</span></button>` : ''}
    </div>
  </div>

  <div class="tab-content active" id="tab-spec">
    <div class="content rendered-md">${md.render(specBody)}</div>
  </div>

  ${hasPlan ? `<div class="tab-content" id="tab-plan"><div class="content rendered-md">${planRendered}</div></div>` : ''}
  ${hasImpl ? `<div class="tab-content" id="tab-impl"><div class="content rendered-md">${implRendered}</div></div>` : ''}
  ${hasRevw ? `<div class="tab-content" id="tab-revw"><div class="content rendered-md">${revwRendered}</div></div>` : ''}
  ${hasLegacyChanges ? `<div class="tab-content" id="tab-changes"><div class="content rendered-md">${changesRendered}</div></div>` : ''}

  <script>
    const vscode = acquireVsCodeApi();
    vscode.setState(${JSON.stringify({ tasksDir: this.tasksDir, taskId: this.taskId })});

    document.querySelectorAll('.tab').forEach(tab => {
      tab.addEventListener('click', (e) => {
        if (e.target.closest('.tab-open-icon')) return;
        document.querySelectorAll('.tab').forEach(t => t.classList.remove('active'));
        document.querySelectorAll('.tab-content').forEach(c => c.classList.remove('active'));
        tab.classList.add('active');
        const target = document.getElementById('tab-' + tab.dataset.tab);
        if (target) target.classList.add('active');
      });
    });

    document.querySelectorAll('.tab-open-icon').forEach(icon => {
      icon.addEventListener('click', (e) => {
        e.stopPropagation();
        vscode.postMessage({ command: 'openFile', path: icon.dataset.path });
      });
    });

  </script>
</body>
</html>`;
  }
}

const safeRead = (filePath: string): string => {
  try {
    return fs.readFileSync(filePath, 'utf8');
  } catch {
    return '';
  }
};

const parseFrontmatterAndBody = (content: string): { readonly frontmatter: TaskFrontmatter; readonly body: string } => {
  const match = content.match(/^---\n([\s\S]*?)\n---\n?([\s\S]*)$/);
  if (!match) return { frontmatter: {}, body: content.trim() };

  const fmRaw = match[1];
  const body = match[2].trim();

  const get = (key: string): string | undefined => {
    const m = fmRaw.match(new RegExp(`^${key}:\\s*(.+)$`, 'm'));
    return m ? m[1].trim().replace(/^['"]|['"]$/g, '') : undefined;
  };

  const priority = get('priority');
  const rawType = get('type');
  const type: TaskType | undefined = rawType === 'epic' ? 'epic' : rawType === 'change' ? 'change' : undefined;

  return {
    frontmatter: {
      id: get('id'),
      title: get('title'),
      type,
      status: get('status'),
      priority: priority === 'null' ? undefined : priority,
      parentEpic: get('parent_epic'),
      created: get('created'),
    },
    body,
  };
};

const parseYamlMeta = (content: string): TaskFrontmatter => {
  const get = (key: string): string | undefined => {
    const m = content.match(new RegExp(`^${key}:\\s*(.+)$`, 'm'));
    return m ? m[1].trim().replace(/^['"]|['"]$/g, '') : undefined;
  };

  const priority = get('priority');
  const rawType = get('type');
  const type: TaskType | undefined = rawType === 'epic' ? 'epic' : rawType === 'change' ? 'change' : undefined;

  return {
    id: get('id'),
    title: get('title'),
    type,
    status: get('status'),
    priority: priority === 'null' ? undefined : priority,
    parentEpic: get('parent_epic'),
    created: get('created'),
  };
};

const escapeHtml = (text: string): string =>
  text.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;');
