import { computed, ref, watch, type Ref } from 'vue';
import { ElMessage } from 'element-plus';
import { getAiNewsPrefs, putAiNewsPrefs } from '@/api';
import { readDemoCache, removeDemoCache, writeDemoCache, hasDemoCache } from '@/composables/useFormCache';
import { domesticLinkDefs, internationalLinkDefs, type AiNewsLinkDef } from './ai-news-links-data';

export type AiNewsLinkRegion = 'international' | 'domestic';
export type AiNewsColumnId = 'international' | 'domestic' | 'favorites';

export interface AiNewsCustomLink {
    id: string;
    url: string;
    title: string;
    icon: string;
    letter: string;
    color: string;
    region?: AiNewsLinkRegion;
}

export interface AiNewsFavoriteRef {
    type: 'preset' | 'custom';
    id: string;
}

export interface AiNewsUserPrefs {
    hiddenPresetIds: string[];
    customLinks: AiNewsCustomLink[];
    favorites: AiNewsFavoriteRef[];
    presetColumns: Record<string, AiNewsLinkRegion>;
    internationalOrder: string[];
    domesticOrder: string[];
}

export interface ResolvedLink {
    key: string;
    id: string;
    type: 'preset' | 'custom';
    url: string;
    icon: string;
    letter: string;
    color: string;
    presetId?: string;
}

const DEFAULT_PREFS: AiNewsUserPrefs = {
    hiddenPresetIds: [],
    customLinks: [],
    favorites: [],
    presetColumns: {},
    internationalOrder: [],
    domesticOrder: [],
};

const ALL_PRESET_DEFS = [...internationalLinkDefs, ...domesticLinkDefs];
const PRESET_DEF_MAP = new Map(ALL_PRESET_DEFS.map((def) => [def.id, def]));
const PRESET_URLS = new Set(ALL_PRESET_DEFS.map((def) => def.url));

const PALETTE = ['#409EFF', '#67C23A', '#E6A23C', '#F56C6C', '#909399', '#1E88E5', '#00B388', '#7B1FA2'];
const SAVE_DEBOUNCE_MS = 400;
const FAVORITES_SEED_VERSION = 'v3';

type FavoriteSeed =
    | { kind: 'preset'; id: string }
    | { kind: 'custom'; url: string; title: string; region?: AiNewsLinkRegion };

/** 开发者向：置顶收藏 */
const PRIORITY_FAVORITE_SEEDS: FavoriteSeed[] = [
    { kind: 'custom', url: 'https://paperswithcode.com', title: 'Papers with Code' },
    { kind: 'preset', id: 'huggingfacePapers' },
    { kind: 'preset', id: 'jiqizhixin' },
    { kind: 'custom', url: 'https://openai.com/research', title: 'OpenAI Research 博客' },
];

/** 默认收藏（含论文 / 三巨头 / 中文媒体） */
const DEFAULT_FAVORITE_SEEDS: FavoriteSeed[] = [
    ...PRIORITY_FAVORITE_SEEDS,
    { kind: 'preset', id: 'anthropic' },
    { kind: 'preset', id: 'deepmind' },
    { kind: 'preset', id: 'arxiv' },
    { kind: 'custom', url: 'https://www.aiera.com.cn', title: '新智元', region: 'domestic' },
    { kind: 'custom', url: 'https://www.zhihu.com/topic/19551275/hot', title: '知乎·人工智能', region: 'domestic' },
];

let prefsRef: Ref<AiNewsUserPrefs> | null = null;
let loadPromise: Promise<void> | null = null;
let saveTimer: ReturnType<typeof setTimeout> | null = null;
let saveQueued = false;
let saveInFlight = false;
let suppressSave = false;
let saveErrorNotified = false;

export const prefsSyncState = ref<'idle' | 'saving' | 'synced' | 'offline'>('idle');

function legacyStorageKey(): string {
    const user = localStorage.getItem('vuems_name') || 'guest';
    return `ai-news:${user}`;
}

function mirrorStorageKey(): string {
    const user = localStorage.getItem('vuems_name') || 'guest';
    return `ai-news:mirror:${user}`;
}

/** @deprecated 旧版本地缓存，仅用于迁移 */
function prefsStorageKey(): string {
    const user = localStorage.getItem('vuems_name') || 'guest';
    return `ai-news:prefs:${user}`;
}

/** @deprecated 旧版收藏缓存，仅用于迁移 */
function favoritesStorageKey(): string {
    const user = localStorage.getItem('vuems_name') || 'guest';
    return `ai-news:favorites:${user}`;
}

function favoritesSeedFlagKey(): string {
    return `ai-news:favorites-seeded:${FAVORITES_SEED_VERSION}`;
}

function clonePrefs(prefs: AiNewsUserPrefs): AiNewsUserPrefs {
    return {
        hiddenPresetIds: [...prefs.hiddenPresetIds],
        customLinks: prefs.customLinks.map((link) => ({ ...link })),
        favorites: prefs.favorites.map((ref) => ({ ...ref })),
        presetColumns: { ...prefs.presetColumns },
        internationalOrder: [...prefs.internationalOrder],
        domesticOrder: [...prefs.domesticOrder],
    };
}

function saveMirror(prefs: AiNewsUserPrefs) {
    writeDemoCache(mirrorStorageKey(), clonePrefs(prefs));
}

function loadLocalBundle(): AiNewsUserPrefs {
    const mirror = readDemoCache<Partial<AiNewsUserPrefs>>(mirrorStorageKey(), {});
    const mirrorNorm = normalizePrefs({ ...DEFAULT_PREFS, ...mirror });
    if (!isEmptyPrefs(mirrorNorm)) {
        return mirrorNorm;
    }

    const legacyPrefs = readDemoCache<Partial<AiNewsUserPrefs>>(prefsStorageKey(), {});
    const legacyFavorites = readDemoCache<AiNewsFavoriteRef[]>(favoritesStorageKey(), []);
    const legacyAll = readDemoCache<Partial<AiNewsUserPrefs>>(legacyStorageKey(), DEFAULT_PREFS);
    const favorites =
        legacyFavorites.length > 0
            ? legacyFavorites
            : (legacyAll.favorites ?? legacyPrefs.favorites ?? []);

    return normalizePrefs({
        ...DEFAULT_PREFS,
        ...legacyAll,
        ...legacyPrefs,
        favorites,
    });
}

function cleanupLegacyLocalKeys() {
    removeDemoCache(legacyStorageKey());
    removeDemoCache(prefsStorageKey());
    removeDemoCache(favoritesStorageKey());
}

function resolveUrlForRef(ref: AiNewsFavoriteRef, prefs: AiNewsUserPrefs): string | null {
    if (ref.type === 'preset') {
        return PRESET_DEF_MAP.get(ref.id)?.url ?? null;
    }
    return prefs.customLinks.find((link) => link.id === ref.id)?.url ?? null;
}

function resolveSeedToRef(
    seed: FavoriteSeed,
    prefs: AiNewsUserPrefs,
    options?: { createMissing?: boolean },
): AiNewsFavoriteRef | null {
    const createMissing = options?.createMissing ?? true;
    if (seed.kind === 'preset') {
        if (!PRESET_DEF_MAP.has(seed.id)) return null;
        return { type: 'preset', id: seed.id };
    }

    const normalized = normalizeUrl(seed.url);
    if (!normalized) return null;

    let custom = prefs.customLinks.find((link) => normalizeUrl(link.url) === normalized);
    if (!custom && createMissing) {
        const created = createCustomLinkFromUrl(seed.url);
        if (!created) return null;
        created.title = seed.title;
        if (seed.region) created.region = seed.region;
        custom = normalizeCustomLink(created);
        prefs.customLinks.push(custom);
    }
    return custom ? { type: 'custom', id: custom.id } : null;
}

function applyFavoriteSeeds(prefs: AiNewsUserPrefs, existing: AiNewsFavoriteRef[]): AiNewsFavoriteRef[] {
    const result = [...existing];
    const keySeen = new Set(existing.map((ref) => favKey(ref)));
    const urlSeen = new Set(
        existing.map((ref) => resolveUrlForRef(ref, prefs)).filter((url): url is string => Boolean(url)),
    );

    for (const seed of DEFAULT_FAVORITE_SEEDS) {
        const ref = resolveSeedToRef(seed, prefs);
        if (!ref) continue;

        const url = resolveUrlForRef(ref, prefs);
        if (!url || [...urlSeen].some((item) => normalizeUrl(item) === normalizeUrl(url))) continue;

        const key = favKey(ref);
        if (keySeen.has(key)) continue;

        result.push(ref);
        keySeen.add(key);
        urlSeen.add(url);
    }

    return result;
}

function reorderFavoritesPriority(prefs: AiNewsUserPrefs, favorites: AiNewsFavoriteRef[]): AiNewsFavoriteRef[] {
    const priorityKeys: string[] = [];
    for (const seed of PRIORITY_FAVORITE_SEEDS) {
        const ref = resolveSeedToRef(seed, prefs, { createMissing: false });
        if (ref) priorityKeys.push(favKey(ref));
    }

    const keyToRef = new Map(favorites.map((ref) => [favKey(ref), ref]));
    const ordered: AiNewsFavoriteRef[] = [];
    for (const key of priorityKeys) {
        const ref = keyToRef.get(key);
        if (ref) ordered.push(ref);
    }
    for (const ref of favorites) {
        if (!priorityKeys.includes(favKey(ref))) ordered.push(ref);
    }
    return ordered;
}

function applyInitialFavoritesIfNeeded(prefs: AiNewsUserPrefs): boolean {
    if (prefs.favorites.length > 0 || hasDemoCache(favoritesSeedFlagKey())) {
        return false;
    }
    let favorites = applyFavoriteSeeds(prefs, []);
    favorites = reorderFavoritesPriority(prefs, favorites);
    prefs.favorites = favorites;
    writeDemoCache(favoritesSeedFlagKey(), true);
    return favorites.length > 0;
}

function hasUserData(prefs: AiNewsUserPrefs): boolean {
    return (
        prefs.hiddenPresetIds.length > 0 ||
        prefs.customLinks.length > 0 ||
        prefs.favorites.length > 0 ||
        Object.keys(prefs.presetColumns ?? {}).length > 0 ||
        (prefs.internationalOrder?.length ?? 0) > 0 ||
        (prefs.domesticOrder?.length ?? 0) > 0
    );
}

function isEmptyPrefs(prefs: AiNewsUserPrefs): boolean {
    return !hasUserData(prefs);
}

function normalizePrefs(raw: Partial<AiNewsUserPrefs>): AiNewsUserPrefs {
    return {
        hiddenPresetIds: [...(raw.hiddenPresetIds ?? [])],
        customLinks: (raw.customLinks ?? []).map((link) => normalizeCustomLink({ ...link })),
        favorites: (raw.favorites ?? []).map((ref) => ({ ...ref })),
        presetColumns: { ...(raw.presetColumns ?? {}) },
        internationalOrder: [...(raw.internationalOrder ?? [])],
        domesticOrder: [...(raw.domesticOrder ?? [])],
    };
}

function notifySaveErrorOnce() {
    if (saveErrorNotified) return;
    saveErrorNotified = true;
    ElMessage.warning('偏好保存失败，已暂存本地，将自动重试同步');
}

function scheduleSave() {
    if (!prefsRef || suppressSave) return;
    saveQueued = true;
    if (saveTimer) clearTimeout(saveTimer);
    saveTimer = setTimeout(() => {
        saveTimer = null;
        void flushSave();
    }, SAVE_DEBOUNCE_MS);
}

async function flushSave(): Promise<void> {
    if (!prefsRef || !saveQueued) return;
    saveQueued = false;
    if (saveInFlight) {
        scheduleSave();
        return;
    }
    saveInFlight = true;
    prefsSyncState.value = 'saving';
    try {
        const payload = clonePrefs(prefsRef.value);
        await putAiNewsPrefs(payload);
        saveMirror(payload);
        saveErrorNotified = false;
        prefsSyncState.value = 'synced';
    } catch {
        saveMirror(prefsRef.value);
        prefsSyncState.value = 'offline';
        notifySaveErrorOnce();
        saveQueued = true;
        scheduleSave();
    } finally {
        saveInFlight = false;
        if (saveQueued && !saveTimer) {
            scheduleSave();
        }
    }
}

async function persistPrefsToDb(prefs: AiNewsUserPrefs): Promise<boolean> {
    try {
        const payload = clonePrefs(prefs);
        await putAiNewsPrefs(payload);
        saveMirror(payload);
        saveErrorNotified = false;
        prefsSyncState.value = 'synced';
        return true;
    } catch {
        saveMirror(prefs);
        prefsSyncState.value = 'offline';
        notifySaveErrorOnce();
        return false;
    }
}

function hashString(s: string): number {
    let h = 0;
    for (let i = 0; i < s.length; i++) h = (h * 31 + s.charCodeAt(i)) | 0;
    return Math.abs(h);
}

export function domainToColor(host: string): string {
    return PALETTE[hashString(host) % PALETTE.length];
}

export function domainToLetter(host: string): string {
    const clean = host.replace(/^www\./, '');
    const ch = clean.charAt(0);
    return ch ? ch.toUpperCase() : '?';
}

export function normalizeUrl(raw: string): string | null {
    const trimmed = raw.trim();
    if (!trimmed) return null;
    try {
        const url = new URL(trimmed.includes('://') ? trimmed : `https://${trimmed}`);
        if (!['http:', 'https:'].includes(url.protocol)) return null;
        return url.href;
    } catch {
        return null;
    }
}

export function classifyLinkRegion(url: string): AiNewsLinkRegion {
    const host = new URL(url).hostname.toLowerCase().replace(/^www\./, '');
    if (/\.(cn|中国)$/.test(host) || /\.(com|net|org|gov|edu)\.cn$/.test(host)) {
        return 'domestic';
    }
    if (/[\u4e00-\u9fff]/.test(host)) {
        return 'domestic';
    }
    const domesticRoots = domesticLinkDefs.map((def) =>
        new URL(def.url).hostname.toLowerCase().replace(/^www\./, ''),
    );
    if (domesticRoots.some((root) => host === root || host.endsWith(`.${root}`))) {
        return 'domestic';
    }
    const domesticHostHints = ['zhihu.com', 'aiera.com.cn'];
    if (domesticHostHints.some((hint) => host === hint || host.endsWith(`.${hint}`))) {
        return 'domestic';
    }
    return 'international';
}

export function faviconUrlForHost(host: string): string {
    const clean = host.replace(/^www\./, '');
    return `https://www.google.com/s2/favicons?domain=${encodeURIComponent(clean)}&sz=32`;
}

function normalizeCustomLink(link: AiNewsCustomLink): AiNewsCustomLink {
    const host = new URL(link.url).hostname;
    return {
        ...link,
        icon: link.icon || faviconUrlForHost(host),
        letter: link.letter || domainToLetter(host),
        color: link.color || domainToColor(host),
        region: link.region ?? classifyLinkRegion(link.url),
    };
}

export function createCustomLinkFromUrl(raw: string): AiNewsCustomLink | null {
    const url = normalizeUrl(raw);
    if (!url) return null;
    const host = new URL(url).hostname;
    return {
        id: `c${Date.now().toString(36)}${Math.random().toString(36).slice(2, 6)}`,
        url,
        title: host.replace(/^www\./, ''),
        icon: faviconUrlForHost(host),
        letter: domainToLetter(host),
        color: domainToColor(host),
        region: classifyLinkRegion(url),
    };
}

export function itemRefFromKey(key: string): AiNewsFavoriteRef {
    const splitAt = key.indexOf(':');
    return {
        type: key.slice(0, splitAt) as 'preset' | 'custom',
        id: key.slice(splitAt + 1),
    };
}

function favKey(ref: AiNewsFavoriteRef): string {
    return `${ref.type}:${ref.id}`;
}

export function favoriteDevGuideKey(item: ResolvedLink): string | null {
    if (item.type === 'preset' && item.presetId) {
        if (item.presetId === 'huggingfacePapers' || item.presetId === 'jiqizhixin') {
            return item.presetId;
        }
    }
    if (item.url.includes('paperswithcode.com')) return 'paperswithcode';
    if (item.url.includes('openai.com/research')) return 'openaiResearch';
    return null;
}

function defaultPresetRegion(presetId: string): AiNewsLinkRegion {
    return domesticLinkDefs.some((def) => def.id === presetId) ? 'domestic' : 'international';
}

function ensurePrefsRef(): Ref<AiNewsUserPrefs> {
    if (!prefsRef) {
        prefsRef = ref<AiNewsUserPrefs>(normalizePrefs(DEFAULT_PREFS));
        watch(
            prefsRef,
            () => {
                if (!suppressSave && prefsRef) {
                    saveMirror(prefsRef.value);
                }
                scheduleSave();
            },
            { deep: true },
        );
    }
    return prefsRef;
}

export async function loadAiNewsPrefs(): Promise<void> {
    if (loadPromise) return loadPromise;
    loadPromise = (async () => {
        const prefs = ensurePrefsRef();
        suppressSave = true;
        prefsSyncState.value = 'idle';
        try {
            const localBundle = loadLocalBundle();
            let remoteOk = false;
            let remote = normalizePrefs(DEFAULT_PREFS);

            try {
                remote = normalizePrefs((await getAiNewsPrefs()) as Partial<AiNewsUserPrefs>);
                remoteOk = true;
            } catch {
                remoteOk = false;
            }

            if (remoteOk) {
                if (isEmptyPrefs(remote) && !isEmptyPrefs(localBundle)) {
                    prefs.value = clonePrefs(localBundle);
                    applyInitialFavoritesIfNeeded(prefs.value);
                    if (await persistPrefsToDb(prefs.value)) {
                        cleanupLegacyLocalKeys();
                    }
                } else {
                    prefs.value = clonePrefs(remote);
                    let dirty = false;
                    if (prefs.value.favorites.length === 0) {
                        const localFavs = loadLocalBundle().favorites;
                        if (localFavs.length > 0) {
                            prefs.value.favorites = localFavs;
                            dirty = true;
                        }
                    }
                    if (applyInitialFavoritesIfNeeded(prefs.value)) {
                        dirty = true;
                    }
                    saveMirror(prefs.value);
                    if (dirty && (await persistPrefsToDb(prefs.value))) {
                        cleanupLegacyLocalKeys();
                    }
                }
            } else {
                prefs.value = !isEmptyPrefs(localBundle)
                    ? clonePrefs(localBundle)
                    : normalizePrefs(DEFAULT_PREFS);
                applyInitialFavoritesIfNeeded(prefs.value);
                saveMirror(prefs.value);
                prefsSyncState.value = 'offline';
                notifySaveErrorOnce();
            }
        } catch {
            const fallback = loadLocalBundle();
            prefs.value = !isEmptyPrefs(fallback) ? clonePrefs(fallback) : normalizePrefs(DEFAULT_PREFS);
            applyInitialFavoritesIfNeeded(prefs.value);
            saveMirror(prefs.value);
            prefsSyncState.value = 'offline';
        } finally {
            suppressSave = false;
        }
    })();
    try {
        await loadPromise;
    } finally {
        loadPromise = null;
    }
}

export function useAiNewsPrefs() {
    const prefs = ensurePrefsRef();

    const hiddenSet = computed(() => new Set(prefs.value.hiddenPresetIds));

    const resolvePreset = (def: AiNewsLinkDef): ResolvedLink => ({
        key: `preset:${def.id}`,
        id: def.id,
        type: 'preset',
        presetId: def.id,
        url: def.url,
        icon: def.icon,
        letter: def.letter,
        color: def.color,
    });

    const resolveCustom = (link: AiNewsCustomLink): ResolvedLink => ({
        key: `custom:${link.id}`,
        id: link.id,
        type: 'custom',
        url: link.url,
        icon: link.icon,
        letter: link.letter,
        color: link.color,
    });

    const presetRegion = (presetId: string): AiNewsLinkRegion =>
        prefs.value.presetColumns[presetId] ?? defaultPresetRegion(presetId);

    const resolveLinkByKey = (key: string): ResolvedLink | null => {
        const ref = itemRefFromKey(key);
        if (ref.type === 'preset') {
            const def = PRESET_DEF_MAP.get(ref.id);
            if (!def || hiddenSet.value.has(ref.id)) return null;
            return resolvePreset(def);
        }
        const custom = prefs.value.customLinks.find((link) => link.id === ref.id);
        return custom ? resolveCustom(normalizeCustomLink(custom)) : null;
    };

    const applyOrder = (items: ResolvedLink[], orderKeys: string[]): ResolvedLink[] => {
        const map = new Map(items.map((item) => [item.key, item]));
        const ordered: ResolvedLink[] = [];
        const seen = new Set<string>();
        for (const key of orderKeys) {
            const item = map.get(key);
            if (!item || seen.has(item.url)) continue;
            ordered.push(item);
            seen.add(item.url);
        }
        for (const item of items) {
            if (!seen.has(item.url)) {
                ordered.push(item);
                seen.add(item.url);
            }
        }
        return ordered;
    };

    const collectRegionLinks = (region: AiNewsLinkRegion): ResolvedLink[] => {
        const items: ResolvedLink[] = [];
        for (const def of ALL_PRESET_DEFS) {
            if (hiddenSet.value.has(def.id)) continue;
            if (presetRegion(def.id) !== region) continue;
            items.push(resolvePreset(def));
        }
        for (const link of prefs.value.customLinks) {
            const normalized = normalizeCustomLink(link);
            if (normalized.region !== region) continue;
            items.push(resolveCustom(normalized));
        }
        return items;
    };

    const buildColumnLinks = (region: AiNewsLinkRegion): ResolvedLink[] => {
        const order = region === 'international' ? prefs.value.internationalOrder : prefs.value.domesticOrder;
        return applyOrder(collectRegionLinks(region), order);
    };

    const buildFavoriteLinks = (): ResolvedLink[] => {
        const items: ResolvedLink[] = [];
        for (const ref of prefs.value.favorites) {
            const link = resolveLinkByKey(favKey(ref));
            if (link) items.push(link);
        }
        return items;
    };

    const orderField = (column: AiNewsLinkRegion) =>
        column === 'international' ? 'internationalOrder' : 'domesticOrder';

    const setRegionOrder = (region: AiNewsLinkRegion, keys: string[]) => {
        prefs.value[orderField(region)] = keys;
    };

    const assignItemToRegion = (key: string, region: AiNewsLinkRegion) => {
        const ref = itemRefFromKey(key);
        if (ref.type === 'preset') {
            const defaultRegion = defaultPresetRegion(ref.id);
            if (region === defaultRegion) {
                delete prefs.value.presetColumns[ref.id];
            } else {
                prefs.value.presetColumns[ref.id] = region;
            }
            return;
        }
        const custom = prefs.value.customLinks.find((link) => link.id === ref.id);
        if (custom) {
            custom.region = region;
        }
    };

    const removeKeyFromRegionOrders = (key: string) => {
        prefs.value.internationalOrder = prefs.value.internationalOrder.filter((item) => item !== key);
        prefs.value.domesticOrder = prefs.value.domesticOrder.filter((item) => item !== key);
    };

    const removeDuplicateUrlsInRegion = (region: AiNewsLinkRegion, keepKey: string) => {
        const keepLink = resolveLinkByKey(keepKey);
        if (!keepLink) return;
        const links = collectRegionLinks(region);
        for (const link of links) {
            if (link.key === keepKey || link.url !== keepLink.url) continue;
            if (link.type === 'custom') {
                removeCustom(link.id);
            } else {
                hidePreset(link.id);
            }
        }
    };

    const insertKeyAt = (keys: string[], key: string, index: number) => {
        const next = keys.filter((item) => item !== key);
        const safeIndex = Math.max(0, Math.min(index, next.length));
        next.splice(safeIndex, 0, key);
        return next;
    };

    const pinToTop = (column: AiNewsColumnId, key: string) => {
        if (column === 'favorites') {
            const ref = itemRefFromKey(key);
            const fk = favKey(ref);
            const list = prefs.value.favorites.filter((item) => favKey(item) !== fk);
            if (resolveLinkByKey(fk)) {
                list.unshift(ref);
            }
            prefs.value.favorites = list;
            return;
        }
        const region = column;
        assignItemToRegion(key, region);
        setRegionOrder(region, insertKeyAt(prefs.value[orderField(region)], key, 0));
        removeDuplicateUrlsInRegion(region, key);
    };

    const moveItem = (
        key: string,
        fromColumn: AiNewsColumnId,
        toColumn: AiNewsColumnId,
        toIndex: number,
    ) => {
        if (fromColumn === toColumn) {
            if (toColumn === 'favorites') {
                const refs = [...prefs.value.favorites];
                const fromIndex = refs.findIndex((ref) => favKey(ref) === key);
                if (fromIndex < 0) return;
                const [item] = refs.splice(fromIndex, 1);
                const safeIndex = Math.max(0, Math.min(toIndex, refs.length));
                refs.splice(safeIndex, 0, item);
                prefs.value.favorites = refs;
                return;
            }
            const region = toColumn;
            const currentKeys = buildColumnLinks(region).map((item) => item.key);
            const fromIndex = currentKeys.indexOf(key);
            if (fromIndex < 0) return;
            const next = [...currentKeys];
            next.splice(fromIndex, 1);
            const safeIndex = Math.max(0, Math.min(toIndex, next.length));
            next.splice(safeIndex, 0, key);
            setRegionOrder(region, next);
            return;
        }

        if (toColumn === 'favorites') {
            const ref = itemRefFromKey(key);
            if (!resolveLinkByKey(key)) return;
            const fk = favKey(ref);
            const refs = prefs.value.favorites.filter((item) => favKey(item) !== fk);
            const safeIndex = Math.max(0, Math.min(toIndex, refs.length));
            refs.splice(safeIndex, 0, ref);
            prefs.value.favorites = refs;
            return;
        }

        const targetRegion = toColumn;
        assignItemToRegion(key, targetRegion);
        removeKeyFromRegionOrders(key);

        if (fromColumn === 'favorites') {
            removeFavorite(itemRefFromKey(key));
        }

        const targetKeys = buildColumnLinks(targetRegion)
            .map((item) => item.key)
            .filter((item) => item !== key);
        const safeIndex = Math.max(0, Math.min(toIndex, targetKeys.length));
        targetKeys.splice(safeIndex, 0, key);
        setRegionOrder(targetRegion, targetKeys);
        removeDuplicateUrlsInRegion(targetRegion, key);
    };

    const hidePreset = (id: string) => {
        if (!prefs.value.hiddenPresetIds.includes(id)) {
            prefs.value.hiddenPresetIds.push(id);
        }
        const key = `preset:${id}`;
        removeKeyFromRegionOrders(key);
        removeFavorite({ type: 'preset', id });
    };

    const removeCustom = (id: string) => {
        const key = `custom:${id}`;
        prefs.value.customLinks = prefs.value.customLinks.filter((link) => link.id !== id);
        removeKeyFromRegionOrders(key);
        removeFavorite({ type: 'custom', id });
    };

    const addCustom = (link: AiNewsCustomLink) => {
        const normalized = normalizeCustomLink(link);
        const dup =
            PRESET_URLS.has(normalized.url) ||
            prefs.value.customLinks.some((item) => item.url === normalized.url);
        if (dup) return false;
        prefs.value.customLinks.push(normalized);
        const key = `custom:${normalized.id}`;
        const orderFieldName = orderField(normalized.region);
        prefs.value[orderFieldName] = insertKeyAt(prefs.value[orderFieldName], key, 0);
        return true;
    };

    const isFavorite = (ref: AiNewsFavoriteRef) =>
        prefs.value.favorites.some((item) => favKey(item) === favKey(ref));

    const addFavorite = (ref: AiNewsFavoriteRef) => {
        if (isFavorite(ref)) return false;
        prefs.value.favorites.push(ref);
        return true;
    };

    const removeFavorite = (ref: AiNewsFavoriteRef) => {
        prefs.value.favorites = prefs.value.favorites.filter((item) => favKey(item) !== favKey(ref));
    };

    return {
        prefs,
        buildColumnLinks,
        buildFavoriteLinks,
        resolvePreset,
        resolveCustom,
        resolveLinkByKey,
        hidePreset,
        removeCustom,
        addCustom,
        isFavorite,
        addFavorite,
        removeFavorite,
        pinToTop,
        moveItem,
        favKey,
        itemRefFromKey,
    };
}
