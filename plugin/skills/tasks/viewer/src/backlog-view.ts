import * as vscode from 'vscode';
import * as fs from 'fs';
import * as path from 'path';
import { TaskDetailPanel } from './task-detail-panel';

type TaskType = 'epic' | 'change';

type TaskData = {
  readonly id: string;
  readonly title: string;
  readonly type: TaskType;
  readonly parentEpic?: string;
  readonly status: string;
  readonly statusIcon: string;
  readonly priority: string;
  readonly priorityIcon: string;
  readonly relPath: string;
  readonly repos: string;
};

const STATUS_META: Readonly<Record<string, { readonly icon: string; readonly label: string }>> = {
  'Speccing': { icon: '\u{1F4DD}', label: 'Speccing' },
  'Planning': { icon: '\u{1F4D0}', label: 'Planning' },
  'Plan Review': { icon: '\u2705', label: 'Plan Review' },
  'Implementing': { icon: '\u{1F528}', label: 'Implementing' },
  'Reviewing': { icon: '\u{1F50D}', label: 'Reviewing' },
  'Inbox': { icon: '\u{1F4E5}', label: 'Inbox' },
};

const PRIORITY_META: Readonly<Record<string, { readonly icon: string; readonly label: string }>> = {
  'high': { icon: '\u{1F534}', label: 'High' },
  'medium': { icon: '\u{1F7E1}', label: 'Med' },
  'low': { icon: '\u{1F535}', label: 'Low' },
};

const REPO_SHORT: Readonly<Record<string, string>> = {
  'workspace': 'workspace',
  'sdd-core': 'core',
  'sdd-fullstack-typescript-techpack': 'techpack',
  'sdd-vscode-extension': 'vscode',
  '.github': '.github',
};

const PRIORITY_ORDER: ReadonlyArray<{ readonly key: string; readonly icon: string; readonly label: string }> = [
  { key: 'high', icon: '\u{1F534}', label: 'High' },
  { key: 'medium', icon: '\u{1F7E1}', label: 'Medium' },
  { key: 'low', icon: '\u{1F535}', label: 'Low' },
  { key: '', icon: '\u26AA', label: 'Unprioritized' },
];

const SKIP_SECTIONS: ReadonlySet<string> = new Set(['Complete', 'Rejected', 'Consolidated']);
const TASK_RE = /^- \[#(\d+)\]\(([^)]+)\):?\s*(.*)$/;
const SECTION_RE = /^## (.+)$/;
const PRIORITY_RE = /^### (High|Medium|Low|Unprioritized)/i;

const renderRepoTags = (repos: string): string => {
  if (repos === '\u2014') return '';
  const tags = repos.split(', ').map(r => `<span class="repo-tag">${escapeHtml(r)}</span>`).join('');
  return `<div class="task-tags">${tags}</div>`;
};

const renderTask = (t: TaskData, extra: string = '', showToggle: boolean = false): string => {
  const escapedPath = escapeHtml(t.relPath);
  const escapedTitle = escapeHtml(t.title);
  const toggleCol = showToggle ? '<span class="toggle-col"></span>' : '';
  return `<div class="task${showToggle ? ' has-toggle' : ''}" data-path="${escapedPath}" data-tooltip="#${t.id}: ${escapedTitle}">
    ${toggleCol}
    <div class="task-content">
      <div class="task-row">
        <span class="task-id">${t.priorityIcon}#${t.id}</span>
        <span class="task-title">${escapedTitle}</span>
        ${extra}
      </div>
      ${renderRepoTags(t.repos)}
    </div>
  </div>`;
};

const renderEpicGroup = (epic: TaskData, children: ReadonlyArray<TaskData>): string => {
  const escapedPath = escapeHtml(epic.relPath);
  const escapedTitle = escapeHtml(epic.title);
  const childCount = children.length > 0 ? `<span class="child-count">(${children.length})</span>` : '';
  const childRows = children.map(c => renderTask(c)).join('\n');
  const hasChildren = children.length > 0;
  const toggleContent = hasChildren ? '<span class="disclosure">&#9660;</span>' : '';

  return `<div class="epic-group${hasChildren ? '' : ' no-children'}">
    <div class="task has-toggle epic-header${hasChildren ? ' collapsible' : ''}" data-path="${escapedPath}" data-epic-id="${epic.id}" data-tooltip="#${epic.id}: ${escapedTitle}">
      <span class="toggle-col">${toggleContent}</span>
      <div class="task-content">
        <div class="task-row">
          <span class="task-id">${epic.priorityIcon}#${epic.id}</span>
          <span class="type-tag epic-tag">Epic</span>
          <span class="task-title">${escapedTitle}</span>
          ${childCount}
        </div>
        ${renderRepoTags(epic.repos)}
      </div>
    </div>
    ${hasChildren ? `<div class="epic-children" data-parent="${epic.id}">${childRows}</div>` : ''}
  </div>`;
};

/** Render a list of tasks with epic nesting. When the list contains epics,
 *  all top-level items get a fixed-width toggle column for alignment. */
const renderTaskList = (
  items: ReadonlyArray<TaskData>,
  globalChildrenByEpic: ReadonlyMap<string, ReadonlyArray<TaskData>>,
  forceToggle?: boolean,
): string => {
  const hasEpics = forceToggle ?? items.some(t => t.type === 'epic');

  return items
    // Hide children — they only appear nested under their epic
    .filter(t => !t.parentEpic)
    .map(t => {
      if (t.type === 'epic') {
        return renderEpicGroup(t, globalChildrenByEpic.get(t.id) ?? []);
      }
      return renderTask(t, '', hasEpics);
    }).join('\n');
};

/** Render a foldable priority sub-group (used inside Inbox). */
const renderPrioGroup = (
  prio: typeof PRIORITY_ORDER[number],
  items: ReadonlyArray<TaskData>,
  globalChildrenByEpic: ReadonlyMap<string, ReadonlyArray<TaskData>>,
  forceToggle: boolean,
): string => {
  if (items.length === 0) return '';
  return `<div class="prio-group">
    <div class="prio-header">
      <span class="disclosure">&#9660;</span>
      ${prio.icon} ${prio.label} <span class="count">${items.length}</span>
    </div>
    <div class="prio-children">${renderTaskList(items, globalChildrenByEpic, forceToggle)}</div>
  </div>`;
};

export class BacklogViewProvider implements vscode.WebviewViewProvider {
  private view?: vscode.WebviewView;

  constructor(private readonly tasksDir: string) {}

  resolveWebviewView(webviewView: vscode.WebviewView): void {
    this.view = webviewView;
    webviewView.webview.options = { enableScripts: true };

    webviewView.webview.onDidReceiveMessage((msg: { readonly command: string; readonly relPath: string }) => {
      if (msg.command === 'openTask') {
        TaskDetailPanel.show(this.tasksDir, msg.relPath);
      }
    });

    this.update();
  }

  refresh(): void {
    this.update();
  }

  private update(): void {
    if (!this.view) return;
    this.view.webview.html = this.getHtml();
  }

  private getHtml(): string {
    const tasks = this.parseTasks();

    // Group tasks by status (immutable grouping)
    const groups = tasks.reduce<ReadonlyMap<string, ReadonlyArray<TaskData>>>((acc, t) => {
      const existing = acc.get(t.status) ?? [];
      return new Map([...acc, [t.status, [...existing, t]]]);
    }, new Map());

    const highCount = tasks.filter(t => t.priority === 'high').length;
    const medCount = tasks.filter(t => t.priority === 'medium').length;
    const lowCount = tasks.filter(t => t.priority === 'low').length;
    const unprioritized = tasks.filter(t => !t.priority && t.status === 'Inbox').length;

    // Build global children-by-epic map across all tasks
    const globalChildrenByEpic = tasks
      .filter(t => t.parentEpic)
      .reduce<ReadonlyMap<string, ReadonlyArray<TaskData>>>((acc, t) => {
        const existing = acc.get(t.parentEpic!) ?? [];
        return new Map([...acc, [t.parentEpic!, [...existing, t]]]);
      }, new Map());

    const sections = [...groups.entries()].map(([status, items]) => {
      const meta = Object.values(STATUS_META).find(m => m.label === status);
      const icon = meta?.icon ?? '';

      const content = status === 'Inbox'
        ? (() => {
            const inboxHasEpics = items.some(t => t.type === 'epic');
            return PRIORITY_ORDER.map(prio => {
              const prioItems = items.filter(t =>
                prio.key === '' ? !t.priority : t.priority === prio.key,
              );
              return renderPrioGroup(prio, prioItems, globalChildrenByEpic, inboxHasEpics);
            }).join('');
          })()
        : renderTaskList(items, globalChildrenByEpic);

      return `
        <div class="group">
          <div class="group-header">${icon} ${status} <span class="count">${items.length}</span></div>
          ${content}
        </div>`;
    }).join('');

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
    padding: 0 8px 16px;
    margin: 0;
    overflow-x: hidden;
  }
  .summary {
    color: var(--vscode-descriptionForeground);
    padding: 8px 0;
    font-size: 0.85em;
    border-bottom: 1px solid var(--vscode-panel-border);
    margin-bottom: 4px;
  }
  .group { margin-bottom: 2px; }
  .group-header {
    font-weight: 600;
    font-size: 0.85em;
    padding: 8px 4px 4px;
    color: var(--vscode-descriptionForeground);
    text-transform: uppercase;
    letter-spacing: 0.3px;
  }
  .group-header .count {
    opacity: 0.6;
    font-weight: 400;
  }

  /* Task item */
  .task {
    padding: 3px 6px;
    border-radius: 3px;
    cursor: pointer;
    line-height: 1.5;
  }
  .task:hover {
    background: var(--vscode-list-hoverBackground);
  }
  .task.has-toggle {
    display: flex;
    align-items: flex-start;
  }
  .toggle-col {
    width: 14px;
    flex-shrink: 0;
    text-align: center;
    line-height: 1.5;
  }
  .task-content {
    flex: 1;
    min-width: 0;
  }
  .task-row {
    display: flex;
    align-items: baseline;
    gap: 6px;
  }
  .task-id {
    flex-shrink: 0;
    font-variant-numeric: tabular-nums;
    opacity: 0.8;
    min-width: 40px;
  }
  .prio-icon {
    font-size: 0.8em;
    margin-right: 2px;
  }
  .has-toggle .task-id {
    margin-left: 2px;
  }
  .task-title {
    flex: 1;
    min-width: 0;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }
  .task-tags {
    display: flex;
    gap: 4px;
    padding-left: 46px;
    padding-top: 1px;
  }
  .repo-tag {
    font-size: 0.7em;
    color: var(--vscode-descriptionForeground);
    opacity: 0.7;
    border: 1px solid var(--vscode-panel-border);
    border-radius: 8px;
    padding: 0 5px;
  }

  /* Type badges */
  .type-tag {
    font-size: 0.7em;
    padding: 1px 5px;
    border-radius: 3px;
    flex-shrink: 0;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 0.3px;
  }
  .epic-tag {
    color: var(--vscode-editorInfo-foreground, #3794ff);
    background: rgba(55, 148, 255, 0.15);
  }
  .parent-ref {
    font-size: 0.75em;
    color: var(--vscode-descriptionForeground);
    flex-shrink: 0;
    opacity: 0.7;
  }

  /* Disclosure triangle — shared style for both epic and prio groups */
  .disclosure {
    font-size: 0.65em;
    cursor: pointer;
    transition: transform 0.15s ease;
    display: inline-block;
  }

  /* Epic groups */
  .epic-group { margin: 0; }
  .epic-header.collapsible { cursor: pointer; }
  .epic-group.collapsed .toggle-col .disclosure {
    transform: rotate(-90deg);
  }
  .epic-children {
    padding-left: 18px;
    border-left: 1px solid var(--vscode-panel-border);
    margin-left: 9px;
  }
  .epic-group.collapsed .epic-children {
    display: none;
  }
  .child-count {
    font-size: 0.75em;
    opacity: 0.5;
    flex-shrink: 0;
  }

  /* Priority sub-groups (inside Inbox) */
  .prio-group { margin: 0; }
  .prio-header {
    font-weight: 500;
    font-size: 1em;
    padding: 5px 6px;
    margin: 6px 0 2px;
    cursor: pointer;
    color: var(--vscode-foreground);
    opacity: 0.85;
    background: var(--vscode-sideBar-dropBackground, rgba(128, 128, 128, 0.1));
    border-radius: 3px;
  }
  .prio-header .count {
    opacity: 0.5;
    font-weight: 400;
  }
  .prio-group.collapsed > .prio-header .disclosure {
    transform: rotate(-90deg);
  }
  .prio-children {
    padding-left: 6px;
  }
  .prio-group.collapsed > .prio-children {
    display: none;
  }

  /* Tooltip */
  #tooltip {
    display: none;
    position: fixed;
    background: var(--vscode-editorHoverWidget-background, var(--vscode-editor-background));
    color: var(--vscode-editorHoverWidget-foreground, var(--vscode-foreground));
    border: 1px solid var(--vscode-editorHoverWidget-border, var(--vscode-panel-border));
    padding: 4px 8px;
    font-size: 0.85em;
    border-radius: 3px;
    pointer-events: none;
    z-index: 100;
    max-width: min(280px, calc(100vw - 24px));
    word-wrap: break-word;
    white-space: normal;
  }
</style>
</head>
<body>
  <div class="summary">
    <strong>${tasks.length} open</strong> &mdash;
    ${highCount} high, ${medCount} med, ${lowCount} low, ${unprioritized} unprioritized
  </div>
  ${sections}
  <div id="tooltip"></div>
  <script>
    const vscode = acquireVsCodeApi();
    const tooltip = document.getElementById('tooltip');

    // Event delegation for clicks
    document.body.addEventListener('click', (e) => {
      // Priority sub-group toggle (whole header is clickable)
      const prioHeader = e.target.closest('.prio-header');
      if (prioHeader) {
        const group = prioHeader.closest('.prio-group');
        if (group) group.classList.toggle('collapsed');
        return;
      }

      // Epic group toggle (disclosure triangle)
      const disc = e.target.closest('.disclosure');
      if (disc) {
        const group = disc.closest('.epic-group');
        if (group) group.classList.toggle('collapsed');
        return;
      }

      // Task click — open detail panel
      const task = e.target.closest('.task');
      if (task && task.dataset.path) {
        vscode.postMessage({ command: 'openTask', relPath: task.dataset.path });
      }
    });

    // Tooltip on hover (2s delay, tracks target to avoid resets on child elements)
    let tooltipTimer = null;
    let currentTarget = null;
    let mouseX = 0, mouseY = 0;

    function positionTooltip() {
      const pad = 4;
      const rect = tooltip.getBoundingClientRect();
      const vw = document.documentElement.clientWidth;
      const vh = document.documentElement.clientHeight;
      let x = mouseX + 12;
      let y = mouseY + 12;
      if (x + rect.width + pad > vw) x = Math.max(pad, vw - rect.width - pad);
      if (y + rect.height + pad > vh) y = Math.max(pad, mouseY - rect.height - 8);
      tooltip.style.left = x + 'px';
      tooltip.style.top = y + 'px';
    }

    document.body.addEventListener('mousemove', (e) => {
      mouseX = e.clientX;
      mouseY = e.clientY;
      if (tooltip.style.display === 'block') positionTooltip();
    });

    document.body.addEventListener('mouseover', (e) => {
      const target = e.target.closest('[data-tooltip]');
      if (target === currentTarget) return;
      if (tooltipTimer) { clearTimeout(tooltipTimer); tooltipTimer = null; }
      tooltip.style.display = 'none';
      currentTarget = target;
      if (!target) return;
      tooltipTimer = setTimeout(() => {
        tooltip.textContent = target.dataset.tooltip;
        tooltip.style.display = 'block';
        positionTooltip();
      }, 1000);
    });

    document.body.addEventListener('mouseleave', () => {
      if (tooltipTimer) { clearTimeout(tooltipTimer); tooltipTimer = null; }
      tooltip.style.display = 'none';
      currentTarget = null;
    });
  </script>
</body>
</html>`;
  }

  private parseTasks(): ReadonlyArray<TaskData> {
    const indexPath = path.join(this.tasksDir, 'INDEX.md');
    if (!fs.existsSync(indexPath)) return [];

    const content = fs.readFileSync(indexPath, 'utf8');
    const lines = content.split('\n');

    type ParserState = {
      readonly tasks: ReadonlyArray<TaskData>;
      readonly currentStatus: string | null;
      readonly currentPriority: string | undefined;
      readonly skip: boolean;
    };

    const initial: ParserState = { tasks: [], currentStatus: null, currentPriority: undefined, skip: false };

    const result = lines.reduce<ParserState>((state, line) => {
      const sectionMatch = line.match(SECTION_RE);
      if (sectionMatch) {
        const name = sectionMatch[1];
        const skip = SKIP_SECTIONS.has(name);
        return skip || !STATUS_META[name]
          ? { ...state, skip, currentStatus: null }
          : { ...state, skip: false, currentStatus: name, currentPriority: undefined };
      }

      if (state.skip || !state.currentStatus) return state;

      const prioMatch = line.match(PRIORITY_RE);
      if (prioMatch) {
        const p = prioMatch[1].toLowerCase();
        return { ...state, currentPriority: p === 'unprioritized' ? undefined : p };
      }

      const taskMatch = line.match(TASK_RE);
      if (taskMatch) {
        const [, id, relDir, rawTitle] = taskMatch;
        const title = rawTitle.replace(/\s*✓.*$/, '').trim();
        // INDEX.md links to either a directory (0-inbox/67/) or a file (2-planning/67/plan.md)
        // Normalize to always point at task.md inside the task directory
        const taskDirFromLink = relDir.endsWith('/') ? relDir : relDir.replace(/\/[^/]+\.md$/, '/');
        const relPath = `${taskDirFromLink}task.md`;
        const taskFilePath = path.join(this.tasksDir, relPath);
        const frontmatter = readFrontmatter(taskFilePath);
        const rawPriority = frontmatter.priority ?? state.currentPriority;
        const repos = frontmatter.repos.length > 0
          ? frontmatter.repos.map(r => REPO_SHORT[r] ?? r).join(', ')
          : '\u2014';

        const task: TaskData = {
          id,
          title,
          type: frontmatter.type === 'epic' ? 'epic' : 'change',
          parentEpic: frontmatter.parentEpic,
          status: STATUS_META[state.currentStatus].label,
          statusIcon: STATUS_META[state.currentStatus].icon,
          priority: rawPriority ?? '',
          priorityIcon: '',
          relPath,
          repos,
        };
        return { ...state, tasks: [...state.tasks, task] };
      }

      return state;
    }, initial);

    // Resolve "inherit" priority from parent epic and set icons
    const taskById = new Map(result.tasks.map(t => [t.id, t]));
    return result.tasks.map(t => {
      let priority = t.priority;
      if (priority === 'inherit' && t.parentEpic) {
        const parent = taskById.get(t.parentEpic);
        priority = parent ? parent.priority : '';
      }
      const prioMeta = priority ? PRIORITY_META[priority] : undefined;
      const priorityIcon = prioMeta
        ? `<span class="prio-icon">${prioMeta.icon}</span>`
        : '<span class="prio-icon">\u26AA</span>';
      return { ...t, priority, priorityIcon };
    });
  }
}

const readFrontmatter = (filePath: string): { readonly priority?: string; readonly repos: ReadonlyArray<string>; readonly type?: TaskType; readonly parentEpic?: string } => {
  try {
    const content = fs.readFileSync(filePath, 'utf8');
    const fmMatch = content.match(/^---\n([\s\S]*?)\n---/);
    if (!fmMatch) return { repos: [] };
    const fm = fmMatch[1];

    const priorityMatch = fm.match(/priority:\s*(\w+)/);
    const priority = priorityMatch?.[1] === 'null' ? undefined : priorityMatch?.[1];

    const typeMatch = fm.match(/type:\s*(\w+)/);
    const type: TaskType | undefined = typeMatch?.[1] === 'epic' ? 'epic' : undefined;

    const parentEpicMatch = fm.match(/parent_epic:\s*(\d+)/);
    const parentEpic = parentEpicMatch?.[1];

    const reposMatch = fm.match(/repos:\s*\[([^\]]*)\]/);
    const repos = reposMatch
      ? reposMatch[1].split(',').map(r => r.trim().replace(/['"]/g, '')).filter(Boolean)
      : [];

    return { priority, repos, type, parentEpic };
  } catch {
    return { repos: [] };
  }
};

const escapeHtml = (text: string): string =>
  text.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;');
