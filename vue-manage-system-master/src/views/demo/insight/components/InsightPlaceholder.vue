<template>
    <el-empty :description="`${title} · ${phase} ${t('pages.insight.comingSoon')}`" />
</template>

<script setup lang="ts">
import { useI18n } from 'vue-i18n';

defineProps<{ title: string; phase: string }>();
const { t } = useI18n();
</script>
