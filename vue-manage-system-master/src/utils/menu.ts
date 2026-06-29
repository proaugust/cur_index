import type { Menus } from '@/types/menu';

export function filterMenuByPermiss(items: Menus[], keys: string[]): Menus[] {
    const result: Menus[] = [];
    for (const item of items) {
        if (item.children?.length) {
            const children = filterMenuByPermiss(item.children, keys);
            if (keys.includes(item.id) || children.length > 0) {
                result.push({ ...item, children });
            }
            continue;
        }
        if (keys.includes(item.id)) {
            result.push({ ...item });
        }
    }
    return result;
}
