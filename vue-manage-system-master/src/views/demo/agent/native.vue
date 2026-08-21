<template>
    <AgentPanel engine="native" :title="t('pages.agent.nativeSection')" />
</template>

<script setup lang="ts" name="demo-agent-native">
import { useI18n } from 'vue-i18n';
import AgentPanel from './agent-panel.vue';

const { t } = useI18n();
</script>
