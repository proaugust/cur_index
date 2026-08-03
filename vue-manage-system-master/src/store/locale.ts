import { defineStore } from 'pinia';
import i18n, { getStoredLocale, persistLocale, type AppLocale } from '@/i18n';

export const useLocaleStore = defineStore('locale', {
    state: () => ({
        locale: getStoredLocale() as AppLocale,
    }),
    actions: {
        setLocale(locale: AppLocale) {
            this.locale = locale;
            i18n.global.locale.value = locale;
            persistLocale(locale);
        },
        toggleLocale() {
            const order: AppLocale[] = ['en-US', 'zh-CN', 'ja-JP'];
            const next = order[(order.indexOf(this.locale) + 1) % order.length];
            this.setLocale(next);
        },
    },
});
