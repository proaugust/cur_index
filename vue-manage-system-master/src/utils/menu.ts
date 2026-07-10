import type { Menus } from '@/types/menu';

function hasMenuItemPermiss(keys: string[], menuId: string): boolean {
    if (keys.includes(menuId)) return true;
    const prefix = `${menuId}.`;
    return keys.some((code) => code.startsWith(prefix));
}

export function filterMenuByPermiss(items: Menus[], keys: string[]): Menus[] {
    const result: Menus[] = [];
    for (const item of items) {
        if (item.children?.length) {
            const children = filterMenuByPermiss(item.children, keys);
            if (hasMenuItemPermiss(keys, item.id) || children.length > 0) {
                result.push({ ...item, children });
            }
            continue;
        }
        if (hasMenuItemPermiss(keys, item.id)) {
            result.push({ ...item });
        }
    }
    return result;
}
