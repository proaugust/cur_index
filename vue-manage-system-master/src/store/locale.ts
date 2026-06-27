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
            this.setLocale(this.locale === 'zh-CN' ? 'ja-JP' : 'zh-CN');
        },
    },
});
