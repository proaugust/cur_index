<template>
    <div class="container rag-page">
        <div class="page-title-bar mgb20">
            <span class="page-title">{{ t('pages.rag.title') }}</span>
            <FeatureIntroIcon
                page-key="rag"
                section-key="page"
                :intros="intros"
                :title="t('pages.rag.title')"
                @saved="setIntro"
            />
        </div>
        <LazyApiDebugPanel
            endpoint-key="document"
            intro-page-key="rag"
            :intros="intros"
            @intro-saved="setIntro"
        />
    </div>
</template>

<script setup lang="ts" name="demo-rag">
import { useI18n } from 'vue-i18n';
import LazyApiDebugPanel from '@/components/lazy-api-debug-panel.vue';
import FeatureIntroIcon from '@/components/feature-intro-icon.vue';
import { useFeatureIntros } from '@/composables/useFeatureIntros';

const { t } = useI18n();
const { intros, setIntro } = useFeatureIntros('rag');
</script>

<style scoped>
.page-title-bar {
    display: inline-flex;
    align-items: center;
    padding: 4px 0;
}

.page-title {
    font-size: 18px;
    font-weight: 600;
    color: #303133;
}

.mgb20 {
    margin-bottom: 16px;
}
</style>
