import type { StreamEvent } from './types';

export interface Connector {
	type: 'branch-out' | 'merge-in' | 'unmerge-out';
	fromColumn: number;
	toColumn: number;
}

export interface GraphNode {
	id: string;
	event: StreamEvent;
	column: number;
	branchId: string | null;
	branchLabel: string | null;
	collapsed?: { count: number; events: StreamEvent[] };
	connectors: Connector[];
}

export interface GraphRow {
	node: GraphNode;
	activeBranches: Set<number>;
}

/**
 * Transform a flat chronological list of StreamEvents into a branching graph.
 *
 * Column 0 is always the main recipe line. Each fork gets its own column
 * (1, 2, 3…) assigned in the order of first "forked" event.
 *
 * Consecutive fork edits on the same branch are collapsed into a single node.
 */
export function buildGraph(events: StreamEvent[]): GraphRow[] {
	// Pass 1: assign columns to each fork_slug in order of first "forked" event
	const branchColumns = new Map<string, number>();
	const branchLabels = new Map<string, string>();
	let nextCol = 1;

	for (const ev of events) {
		if (ev.type === 'forked' && ev.fork_slug && !branchColumns.has(ev.fork_slug)) {
			branchColumns.set(ev.fork_slug, nextCol++);
			branchLabels.set(ev.fork_slug, ev.fork_name ?? ev.fork_slug);
		}
	}

	// State: which branches are currently active (open / not merged)
	const active = new Set<number>();
	// Pending fork edits waiting to be flushed as collapsed nodes
	const pendingEdits = new Map<string, StreamEvent[]>();

	const rows: GraphRow[] = [];
	let nodeIdx = 0;

	function flushPendingEdits(forkSlug: string) {
		const pending = pendingEdits.get(forkSlug);
		if (!pending || pending.length === 0) return;
		const col = branchColumns.get(forkSlug)!;
		const label = branchLabels.get(forkSlug) ?? null;

		if (pending.length === 1) {
			rows.push({
				node: {
					id: `node-${nodeIdx++}`,
					event: pending[0],
					column: col,
					branchId: forkSlug,
					branchLabel: null,
					connectors: []
				},
				activeBranches: new Set(active)
			});
		} else {
			rows.push({
				node: {
					id: `node-${nodeIdx++}`,
					event: pending[pending.length - 1],
					column: col,
					branchId: forkSlug,
					branchLabel: null,
					collapsed: { count: pending.length, events: [...pending] },
					connectors: []
				},
				activeBranches: new Set(active)
			});
		}
		pendingEdits.set(forkSlug, []);
	}

	// Pass 2: walk events chronologically and build rows
	// Dispatch on event type first — merge/unmerge always go on column 0
	// regardless of whether fork_slug is set (backend enrichment adds it).
	for (const ev of events) {
		if (ev.type === 'forked' && ev.fork_slug) {
			// Fork creation — place on fork column, add branch-out connector
			const col = branchColumns.get(ev.fork_slug) ?? 0;
			active.add(col);
			rows.push({
				node: {
					id: `node-${nodeIdx++}`,
					event: ev,
					column: col,
					branchId: ev.fork_slug,
					branchLabel: branchLabels.get(ev.fork_slug) ?? null,
					connectors: [{ type: 'branch-out', fromColumn: 0, toColumn: col }]
				},
				activeBranches: new Set(active)
			});
		} else if (ev.type === 'edited' && ev.fork_slug) {
			// Fork edit — accumulate for collapsing
			if (!pendingEdits.has(ev.fork_slug)) pendingEdits.set(ev.fork_slug, []);
			pendingEdits.get(ev.fork_slug)!.push(ev);
		} else if (ev.type === 'merged') {
			// Merge event (always column 0) — flush fork edits, add merge-in connector
			const mergedSlug = ev.fork_slug ?? findForkSlugByName(ev, branchColumns, branchLabels);
			const mergeCol = mergedSlug ? branchColumns.get(mergedSlug) ?? 0 : 0;
			if (mergedSlug) flushPendingEdits(mergedSlug);

			const connectors: Connector[] = [];
			if (mergeCol > 0) {
				connectors.push({ type: 'merge-in', fromColumn: mergeCol, toColumn: 0 });
				active.delete(mergeCol);
			}

			rows.push({
				node: {
					id: `node-${nodeIdx++}`,
					event: ev,
					column: 0,
					branchId: null,
					branchLabel: null,
					connectors
				},
				activeBranches: new Set(active)
			});
		} else if (ev.type === 'unmerged') {
			// Unmerge event (always column 0) — reopen the branch
			const unmergedSlug = ev.fork_slug ?? findForkSlugByName(ev, branchColumns, branchLabels);
			const unmergeCol = unmergedSlug ? branchColumns.get(unmergedSlug) ?? 0 : 0;

			const connectors: Connector[] = [];
			if (unmergeCol > 0) {
				active.add(unmergeCol);
				connectors.push({ type: 'unmerge-out', fromColumn: 0, toColumn: unmergeCol });
			}

			rows.push({
				node: {
					id: `node-${nodeIdx++}`,
					event: ev,
					column: 0,
					branchId: null,
					branchLabel: null,
					connectors
				},
				activeBranches: new Set(active)
			});
		} else {
			// Main-branch event (created, edited without fork_slug, etc.)
			rows.push({
				node: {
					id: `node-${nodeIdx++}`,
					event: ev,
					column: 0,
					branchId: null,
					branchLabel: null,
					connectors: []
				},
				activeBranches: new Set(active)
			});
		}
	}

	// Flush remaining pending edits for open (unmerged) forks
	for (const [forkSlug] of pendingEdits) {
		flushPendingEdits(forkSlug);
	}

	return rows;
}

/**
 * For merge/unmerge events where fork_slug might already be set from the backend
 * enrichment but fork_name matching is a fallback.
 */
function findForkSlugByName(
	ev: StreamEvent,
	branchColumns: Map<string, number>,
	branchLabels: Map<string, string>
): string | undefined {
	// The backend now enriches fork_slug on merge/unmerge events,
	// but if it's missing, try to match by fork_name from the message
	const match = ev.message.match(/(?:Merged|Unmerged) fork '(.+)'/);
	if (!match) return undefined;
	const name = match[1];
	for (const [slug, label] of branchLabels) {
		if (label === name) return slug;
	}
	return undefined;
}

/** Total number of columns needed for the graph. */
export function totalColumns(rows: GraphRow[]): number {
	let max = 0;
	for (const row of rows) {
		if (row.node.column > max) max = row.node.column;
		for (const c of row.activeBranches) {
			if (c > max) max = c;
		}
	}
	return max + 1;
}
