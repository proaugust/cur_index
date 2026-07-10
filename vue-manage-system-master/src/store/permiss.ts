import { defineStore } from 'pinia';

export const usePermissStore = defineStore('permiss', {
    state: () => {
        const saved = localStorage.getItem('vuems_permissions');
        const key = saved ? (JSON.parse(saved) as string[]) : [];
        return {
            key,
        };
    },
    getters: {
        menuKeys(state): string[] {
            return state.key.filter((code) => !code.includes('.'));
        },
        apiKeys(state): string[] {
            return state.key.filter((code) => code.includes('.'));
        },
    },
    actions: {
        handleSet(val: string[]) {
            this.key = val;
            localStorage.setItem('vuems_permissions', JSON.stringify(val));
        },
        has(code: string) {
            return this.key.includes(code);
        },
        hasMenu(code: string) {
            return this.has(code);
        },
        /** 路由守卫：有菜单码或任一子 API 权限即可进入页面 */
        hasRoutePermiss(menuCode: string) {
            if (this.has(menuCode)) return true;
            const prefix = `${menuCode}.`;
            return this.key.some((code) => code.startsWith(prefix));
        },
        hasApi(menuCode: string, apiId: string) {
            return this.has(`${menuCode}.${apiId}`);
        },
        clear() {
            this.key = [];
            localStorage.removeItem('vuems_permissions');
        },
    },
});
