import { ref, watch, type Ref } from 'vue';

const PREFIX = 'vuems_demo:';

export function readDemoCache<T>(key: string, fallback: T): T {
    try {
        const raw = localStorage.getItem(PREFIX + key);
        if (raw == null) return fallback;
        return JSON.parse(raw) as T;
    } catch {
        return fallback;
    }
}

export function writeDemoCache(key: string, value: unknown): void {
    try {
        localStorage.setItem(PREFIX + key, JSON.stringify(value));
    } catch {
        // ignore quota errors
    }
}

export function hasDemoCache(key: string): boolean {
    return localStorage.getItem(PREFIX + key) != null;
}

export function removeDemoCache(key: string): void {
    localStorage.removeItem(PREFIX + key);
}

/** ref 与 localStorage 双向同步，适合业务展示页输入栏草稿缓存 */
export function useCachedRef<T>(key: string, defaultValue: T): Ref<T> {
    const state = ref(readDemoCache(key, defaultValue)) as Ref<T>;
    watch(state, (val) => writeDemoCache(key, val), { deep: true });
    return state;
}
