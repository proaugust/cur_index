<template>
	<el-config-provider :locale="elementLocale">
		<router-view />
	</el-config-provider>
</template>

<script setup lang="ts">
import { computed } from 'vue';
import { useI18n } from 'vue-i18n';
import { ElConfigProvider } from 'element-plus';
import zhCn from 'element-plus/es/locale/lang/zh-cn';
import ja from 'element-plus/es/locale/lang/ja';
import { useThemeStore } from './store/theme';

const { locale } = useI18n();
const theme = useThemeStore();
theme.initTheme();

const elementLocale = computed(() => (locale.value === 'ja-JP' ? ja : zhCn));
</script>
<style>
@import './assets/css/main.css';
</style>
