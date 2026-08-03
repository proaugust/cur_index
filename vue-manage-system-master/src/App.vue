<template>
	<el-config-provider :locale="elementLocale">
		<router-view />
	</el-config-provider>
</template>

<script setup lang="ts">
import { computed, onMounted } from 'vue';
import { useI18n } from 'vue-i18n';
import { ElConfigProvider } from 'element-plus';
import zhCn from 'element-plus/es/locale/lang/zh-cn';
import ja from 'element-plus/es/locale/lang/ja';
import en from 'element-plus/es/locale/lang/en';
import { fetchMe } from '@/api';
import { usePermissStore } from './store/permiss';
import { useThemeStore } from './store/theme';

const { locale } = useI18n();
const theme = useThemeStore();
const permiss = usePermissStore();
theme.initTheme();

const elementLocale = computed(() => {
    if (locale.value === 'ja-JP') return ja;
    if (locale.value === 'en-US') return en;
    return zhCn;
});

onMounted(async () => {
    const token = localStorage.getItem('access_token');
    if (!token) return;
    try {
        const res = await fetchMe();
        if (res.data?.permissions?.length) {
            permiss.handleSet(res.data.permissions);
        }
    } catch {
        // 忽略：token 失效时由请求拦截器跳转登录
    }
});
</script>
<style>
@import './assets/css/main.css';
</style>
