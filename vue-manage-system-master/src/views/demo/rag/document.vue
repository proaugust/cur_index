<template>
    <div class="container rag-page">
        <RagPageHeader :title="t('pages.rag.documentSection')" />
        <LazyApiDebugPanel
            endpoint-key="document"
            intro-page-key="rag"
            :intros="intros"
            @intro-saved="setIntro"
        />
    </div>
</template>

<script setup lang="ts" name="demo-rag-document">
import { useI18n } from 'vue-i18n';
import LazyApiDebugPanel from '@/components/lazy-api-debug-panel.vue';
import RagPageHeader from '@/views/demo/rag/rag-page-header.vue';
import { useFeatureIntros } from '@/composables/useFeatureIntros';

const { t } = useI18n();
const { intros, setIntro } = useFeatureIntros('rag');
</script>
