<template>
    <div class="container rag-page">
        <RagPageHeader :title="t('pages.rag.corporaSection')" />
        <LazyApiDebugPanel
            endpoint-key="corpora"
            intro-page-key="rag"
            :intros="intros"
            @intro-saved="setIntro"
        >
            <template #panel-corpora-import>
                <CorporaImportPanel intro-page-key="rag" :intros="intros" @intro-saved="setIntro" />
            </template>
            <template #panel-corpora-search>
                <CorporaBrowsePanel intro-page-key="rag" :intros="intros" @intro-saved="setIntro" />
            </template>
        </LazyApiDebugPanel>
    </div>
</template>

<script setup lang="ts" name="demo-rag-corpora">
import { useI18n } from 'vue-i18n';
import LazyApiDebugPanel from '@/components/lazy-api-debug-panel.vue';
import RagPageHeader from '@/views/demo/rag/rag-page-header.vue';
import CorporaBrowsePanel from '@/views/demo/corpora-browse-panel.vue';
import CorporaImportPanel from '@/views/demo/corpora-import-panel.vue';
import { useFeatureIntros } from '@/composables/useFeatureIntros';

const { t } = useI18n();
const { intros, setIntro } = useFeatureIntros('rag');
</script>
