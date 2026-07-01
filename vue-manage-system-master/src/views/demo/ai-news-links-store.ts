import { computed } from 'vue';
import { useCachedRef } from '@/composables/useFormCache';
import type { AiNewsLinkDef } from './ai-news-links-data';

export interface AiNewsCustomLink {
    id: string;
    url: string;
    title: string;
    icon: string;
    letter: string;
    color: string;
}

export interface AiNewsFavoriteRef {
    type: 'preset' | 'custom';
    id: string;
}

export interface AiNewsUserPrefs {
    hiddenPresetIds: string[];
    customLinks: AiNewsCustomLink[];
    favorites: AiNewsFavoriteRef[];
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
};

const PALETTE = ['#409EFF', '#67C23A', '#E6A23C', '#F56C6C', '#909399', '#1E88E5', '#00B388', '#7B1FA2'];

function storageKey(): string {
    const user = localStorage.getItem('vuems_name') || 'guest';
    return `ai-news:${user}`;
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

export function createCustomLinkFromUrl(raw: string): AiNewsCustomLink | null {
    const url = normalizeUrl(raw);
    if (!url) return null;
    const host = new URL(url).hostname;
    return {
        id: `c${Date.now().toString(36)}${Math.random().toString(36).slice(2, 6)}`,
        url,
        title: host.replace(/^www\./, ''),
        icon: `${new URL(url).origin}/favicon.ico`,
        letter: domainToLetter(host),
        color: domainToColor(host),
    };
}

function favKey(ref: AiNewsFavoriteRef): string {
    return `${ref.type}:${ref.id}`;
}

export function useAiNewsPrefs() {
    const prefs = useCachedRef<AiNewsUserPrefs>(storageKey(), DEFAULT_PREFS);

    const hiddenSet = computed(() => new Set(prefs.value.hiddenPresetIds));

    const filterPresets = (defs: AiNewsLinkDef[]) =>
        defs.filter((d) => !hiddenSet.value.has(d.id));

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

    const hidePreset = (id: string) => {
        if (!prefs.value.hiddenPresetIds.includes(id)) {
            prefs.value.hiddenPresetIds.push(id);
        }
        removeFavorite({ type: 'preset', id });
    };

    const removeCustom = (id: string) => {
        prefs.value.customLinks = prefs.value.customLinks.filter((c) => c.id !== id);
        removeFavorite({ type: 'custom', id });
    };

    const addCustom = (link: AiNewsCustomLink) => {
        const dup = prefs.value.customLinks.some((c) => c.url === link.url);
        if (dup) return false;
        prefs.value.customLinks.push(link);
        return true;
    };

    const isFavorite = (ref: AiNewsFavoriteRef) =>
        prefs.value.favorites.some((f) => favKey(f) === favKey(ref));

    const addFavorite = (ref: AiNewsFavoriteRef) => {
        if (isFavorite(ref)) return false;
        prefs.value.favorites.push(ref);
        return true;
    };

    const removeFavorite = (ref: AiNewsFavoriteRef) => {
        prefs.value.favorites = prefs.value.favorites.filter((f) => favKey(f) !== favKey(ref));
    };

    const moveFavorite = (from: number, to: number) => {
        const list = [...prefs.value.favorites];
        if (from < 0 || from >= list.length || to < 0 || to >= list.length) return;
        const [item] = list.splice(from, 1);
        list.splice(to, 0, item);
        prefs.value.favorites = list;
    };

    return {
        prefs,
        hiddenSet,
        filterPresets,
        resolvePreset,
        resolveCustom,
        hidePreset,
        removeCustom,
        addCustom,
        isFavorite,
        addFavorite,
        removeFavorite,
        moveFavorite,
        favKey,
    };
}
