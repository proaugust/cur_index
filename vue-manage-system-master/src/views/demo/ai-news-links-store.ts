import { computed, ref, watch, type Ref } from 'vue';
import { ElMessage } from 'element-plus';
import { createAiNewsLink, getAiNewsBoard, putAiNewsBoard, type AiNewsBoard, type AiNewsLinkItem } from '@/api';

export type AiNewsColumnId = 'international' | 'domestic' | 'favorites';
export type ResolvedLink = AiNewsLinkItem & { key: string; stableKey: string };

const SAVE_DEBOUNCE_MS = 400;

let boardRef: Ref<AiNewsBoard> | null = null;
let saveTimer: ReturnType<typeof setTimeout> | null = null;
let saveQueued = false;
let saveInFlight = false;
let suppressSave = false;
let lastSyncedFingerprint = '';

export const prefsSyncState = ref<'idle' | 'saving' | 'synced' | 'offline'>('idle');

function emptyBoard(): AiNewsBoard {
    return { international: [], domestic: [], favorites: [] };
}

function linkStableKey(item: AiNewsLinkItem): string {
    return item.slug || item.url;
}

function withKeys(items: AiNewsLinkItem[]): ResolvedLink[] {
    return items.map((item) => ({
        ...item,
        key: String(item.id),
        stableKey: linkStableKey(item),
    }));
}

function boardFingerprint(board: AiNewsBoard): string {
    return (['international', 'domestic', 'favorites'] as const)
        .map((col) => board[col].map((item) => `${item.slug ?? ''}\t${item.url}\t${item.name}`).join('\n'))
        .join('\n---\n');
}

function applyBoardSilently(target: AiNewsBoard, source: AiNewsBoard) {
    suppressSave = true;
    try {
        applyBoard(target, source);
        lastSyncedFingerprint = boardFingerprint(target);
    } finally {
        suppressSave = false;
    }
}

function toEntry(item: AiNewsLinkItem) {
    return {
        slug: item.slug,
        url: item.url,
        name: item.name,
        description: item.description,
        icon: item.icon,
        letter: item.letter,
        color: item.color,
    };
}

function boardToPayload(board: AiNewsBoard) {
    return {
        international: board.international.map(toEntry),
        domestic: board.domestic.map(toEntry),
        favorites: board.favorites.map(toEntry),
    };
}

function applyBoard(target: AiNewsBoard, source: AiNewsBoard) {
    target.international = [...source.international];
    target.domestic = [...source.domestic];
    target.favorites = [...source.favorites];
}

function ensureBoardRef(): Ref<AiNewsBoard> {
    if (!boardRef) {
        boardRef = ref<AiNewsBoard>(emptyBoard());
        watch(
            boardRef,
            () => {
                if (!suppressSave) scheduleSave();
            },
            { deep: true },
        );
    }
    return boardRef;
}

function scheduleSave() {
    if (!boardRef || suppressSave) return;
    saveQueued = true;
    if (saveTimer) clearTimeout(saveTimer);
    saveTimer = setTimeout(() => {
        saveTimer = null;
        void flushSave();
    }, SAVE_DEBOUNCE_MS);
}

async function flushSave() {
    if (!boardRef || !saveQueued) return;
    saveQueued = false;
    if (saveInFlight) {
        scheduleSave();
        return;
    }
    const fingerprint = boardFingerprint(boardRef.value);
    if (fingerprint === lastSyncedFingerprint) {
        return;
    }
    saveInFlight = true;
    prefsSyncState.value = 'saving';
    try {
        const { data } = await putAiNewsBoard(boardToPayload(boardRef.value));
        applyBoardSilently(boardRef.value, data as AiNewsBoard);
        prefsSyncState.value = 'synced';
    } catch {
        prefsSyncState.value = 'offline';
        ElMessage.warning('导航保存失败，将自动重试');
        saveQueued = true;
        scheduleSave();
    } finally {
        saveInFlight = false;
        if (saveQueued && !saveTimer) scheduleSave();
    }
}

export async function loadAiNewsBoard(): Promise<void> {
    const board = ensureBoardRef();
    prefsSyncState.value = 'idle';
    try {
        const { data } = await getAiNewsBoard();
        applyBoardSilently(board.value, data as AiNewsBoard);
        prefsSyncState.value = 'synced';
    } catch {
        prefsSyncState.value = 'offline';
    }
}

export function faviconUrlForHost(host: string): string {
    const clean = host.replace(/^www\./, '');
    return `https://www.google.com/s2/favicons?domain=${encodeURIComponent(clean)}&sz=32`;
}

export function favoriteDevGuideKey(item: ResolvedLink): string | null {
    if (item.slug === 'huggingfacePapers' || item.slug === 'jiqizhixin') return item.slug;
    if (item.url.includes('paperswithcode.com')) return 'paperswithcode';
    if (item.url.includes('openai.com/research')) return 'openaiResearch';
    return null;
}

function columnItems(board: AiNewsBoard, column: AiNewsColumnId): AiNewsLinkItem[] {
    return board[column];
}

function setColumnItems(board: AiNewsBoard, column: AiNewsColumnId, items: AiNewsLinkItem[]) {
    board[column] = items;
}

function findItem(board: AiNewsBoard, key: string): { column: AiNewsColumnId; index: number; item: AiNewsLinkItem } | null {
    for (const column of ['international', 'domestic', 'favorites'] as AiNewsColumnId[]) {
        const index = columnItems(board, column).findIndex((item) => String(item.id) === key);
        if (index >= 0) {
            return { column, index, item: columnItems(board, column)[index] };
        }
    }
    return null;
}

function sameLink(a: AiNewsLinkItem, b: AiNewsLinkItem): boolean {
    if (a.slug && b.slug) return a.slug === b.slug;
    return a.url === b.url;
}

function isFavoriteLink(board: AiNewsBoard, item: AiNewsLinkItem): boolean {
    return board.favorites.some((favorite) => sameLink(favorite, item));
}

function insertAt<T>(list: T[], index: number, item: T): T[] {
    const next = [...list];
    const safeIndex = Math.max(0, Math.min(index, next.length));
    next.splice(safeIndex, 0, item);
    return next;
}

export function useAiNewsBoard() {
    const board = ensureBoardRef();

    const internationalLinks = computed(() => withKeys(board.value.international));
    const domesticLinks = computed(() => withKeys(board.value.domestic));
    const favoriteLinks = computed(() => withKeys(board.value.favorites));

    const pinToTop = (column: AiNewsColumnId, key: string) => {
        const found = findItem(board.value, key);
        if (!found) return;
        const items = columnItems(board.value, column).filter((item) => String(item.id) !== key);
        setColumnItems(board.value, column, [found.item, ...items]);
    };

    const moveItem = (key: string, fromColumn: AiNewsColumnId, toColumn: AiNewsColumnId, toIndex: number) => {
        const found = findItem(board.value, key);
        if (!found) return;
        const source = columnItems(board.value, fromColumn).filter((item) => String(item.id) !== key);
        setColumnItems(board.value, fromColumn, source);
        const target = columnItems(board.value, toColumn).filter((item) => String(item.id) !== key);
        setColumnItems(board.value, toColumn, insertAt(target, toIndex, found.item));
    };

    const removeFromBoard = (key: string) => {
        for (const column of ['international', 'domestic', 'favorites'] as AiNewsColumnId[]) {
            setColumnItems(
                board.value,
                column,
                columnItems(board.value, column).filter((item) => String(item.id) !== key),
            );
        }
    };

    const isFavorite = (key: string) => {
        const found = findItem(board.value, key);
        return found ? isFavoriteLink(board.value, found.item) : false;
    };

    const addFavorite = (key: string) => {
        const found = findItem(board.value, key);
        if (!found || isFavoriteLink(board.value, found.item)) return false;
        board.value.favorites = [...board.value.favorites, found.item];
        return true;
    };

    const removeFavorite = (key: string) => {
        const found = findItem(board.value, key);
        if (!found) {
            board.value.favorites = board.value.favorites.filter((item) => String(item.id) !== key);
            return;
        }
        board.value.favorites = board.value.favorites.filter((item) => !sameLink(item, found.item));
    };

    const addCustomByUrl = async (raw: string): Promise<'ok' | 'invalid' | 'duplicate'> => {
        try {
            const { data } = await createAiNewsLink(raw);
            applyBoardSilently(board.value, data as AiNewsBoard);
            prefsSyncState.value = 'synced';
            return 'ok';
        } catch (error) {
            const status = (error as { response?: { status?: number } }).response?.status;
            if (status === 409) return 'duplicate';
            return 'invalid';
        }
    };

    return {
        board,
        internationalLinks,
        domesticLinks,
        favoriteLinks,
        pinToTop,
        moveItem,
        removeFromBoard,
        isFavorite,
        addFavorite,
        removeFavorite,
        addCustomByUrl,
    };
}
