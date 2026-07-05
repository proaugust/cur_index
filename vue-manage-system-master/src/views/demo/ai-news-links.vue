<template>
    <div class="container ai-news-page" v-loading="prefsLoading">
        <el-card shadow="hover">
            <template #header>
                <div class="page-header">
                    <span class="page-title">{{ t('pages.aiNews.title') }}</span>
                </div>
            </template>

            <p class="page-intro">{{ t('pages.aiNews.intro') }}</p>

            <div class="add-bar">
                <el-input
                    v-model="urlInput"
                    :placeholder="t('pages.aiNews.addPlaceholder')"
                    clearable
                    @keyup.enter="onAddUrl"
                />
                <el-button type="primary" :disabled="!urlInput.trim()" @click="onAddUrl">
                    {{ t('pages.aiNews.add') }}
                </el-button>
            </div>

            <p class="drag-hint">{{ t('pages.aiNews.dragHint') }}</p>

            <el-row :gutter="20" class="columns-row">
                <el-col :xs="24" :md="8">
                    <div
                        class="link-section panel-box"
                        :class="{ 'panel-box--drop': dragOverColumn === 'international' }"
                        @dragover.prevent="onColumnDragOver('international')"
                        @dragleave="onColumnDragLeave('international')"
                        @drop.prevent="(event) => onColumnDrop('international', internationalLinks.length, event)"
                    >
                        <div class="section-label">{{ t('pages.aiNews.sectionInternational') }}</div>
                        <div class="link-list">
                            <div
                                v-for="(item, index) in internationalLinks"
                                :key="item.key"
                                class="link-item-wrapper"
                                :class="{
                                    'link-item-wrapper--insert-before': isInsertBefore('international', index),
                                    'link-item-wrapper--insert-after': isInsertAfter('international', index),
                                }"
                                @dragover.prevent="onItemDragOver('international', index, $event)"
                                @drop.prevent.stop="(event) => onColumnDrop('international', index, event)"
                            >
                                <LinkCard
                                    :item="item"
                                    :name="item.name"
                                    :desc="item.description || item.url"
                                    :favorited="isFavoriteItem(item)"
                                    column="international"
                                    :index="index"
                                    @open="openLink"
                                    @delete="onDeleteLink"
                                    @favorite="onToggleFavorite"
                                    @pin-top="onPinTop('international', $event)"
                                    @drag-end="clearDragState"
                                />
                            </div>
                            <div
                                v-if="!internationalLinks.length"
                                class="empty-hint"
                                @dragover.prevent="onColumnDragOver('international')"
                                @drop.prevent="(event) => onColumnDrop('international', 0, event)"
                            >
                                {{ t('pages.aiNews.emptySection') }}
                            </div>
                        </div>
                    </div>
                </el-col>
                <el-col :xs="24" :md="8">
                    <div
                        class="link-section panel-box"
                        :class="{ 'panel-box--drop': dragOverColumn === 'domestic' }"
                        @dragover.prevent="onColumnDragOver('domestic')"
                        @dragleave="onColumnDragLeave('domestic')"
                        @drop.prevent="(event) => onColumnDrop('domestic', domesticLinks.length, event)"
                    >
                        <div class="section-label">{{ t('pages.aiNews.sectionDomestic') }}</div>
                        <div class="link-list">
                            <div
                                v-for="(item, index) in domesticLinks"
                                :key="item.key"
                                class="link-item-wrapper"
                                :class="{
                                    'link-item-wrapper--insert-before': isInsertBefore('domestic', index),
                                    'link-item-wrapper--insert-after': isInsertAfter('domestic', index),
                                }"
                                @dragover.prevent="onItemDragOver('domestic', index, $event)"
                                @drop.prevent.stop="(event) => onColumnDrop('domestic', index, event)"
                            >
                                <LinkCard
                                    :item="item"
                                    :name="item.name"
                                    :desc="item.description || item.url"
                                    :favorited="isFavoriteItem(item)"
                                    column="domestic"
                                    :index="index"
                                    @open="openLink"
                                    @delete="onDeleteLink"
                                    @favorite="onToggleFavorite"
                                    @pin-top="onPinTop('domestic', $event)"
                                    @drag-end="clearDragState"
                                />
                            </div>
                            <div
                                v-if="!domesticLinks.length"
                                class="empty-hint"
                                @dragover.prevent="onColumnDragOver('domestic')"
                                @drop.prevent="(event) => onColumnDrop('domestic', 0, event)"
                            >
                                {{ t('pages.aiNews.emptySection') }}
                            </div>
                        </div>
                    </div>
                </el-col>
                <el-col :xs="24" :md="8">
                    <div
                        class="favorites-panel panel-box"
                        :class="{ 'panel-box--drop': dragOverColumn === 'favorites' }"
                        @dragover.prevent="onColumnDragOver('favorites')"
                        @dragleave="onColumnDragLeave('favorites')"
                        @drop.prevent="(event) => onColumnDrop('favorites', favoriteLinks.length, event)"
                    >
                        <div class="section-label">
                            <el-icon class="fav-icon"><Star /></el-icon>
                            {{ t('pages.aiNews.favorites') }}
                        </div>
                        <p class="fav-hint">{{ t('pages.aiNews.favoritesHint') }}</p>
                        <div class="link-list link-list--grow">
                            <div
                                v-for="(item, index) in favoriteLinks"
                                :key="item.key"
                                class="link-item-wrapper"
                                :class="{
                                    'link-item-wrapper--insert-before': isInsertBefore('favorites', index),
                                    'link-item-wrapper--insert-after': isInsertAfter('favorites', index),
                                }"
                                @dragover.prevent="onItemDragOver('favorites', index, $event)"
                                @drop.prevent.stop="(event) => onColumnDrop('favorites', index, event)"
                            >
                                <LinkCard
                                    :item="item"
                                    :name="item.name"
                                    :desc="displayDescForFavorites(item)"
                                    :favorited="true"
                                    column="favorites"
                                    :index="index"
                                    @open="openLink"
                                    @delete="onRemoveFavorite"
                                    @favorite="onRemoveFavorite"
                                    @pin-top="onPinTop('favorites', $event)"
                                    @drag-end="clearDragState"
                                />
                            </div>
                            <div
                                v-if="!favoriteLinks.length"
                                class="fav-empty fav-empty--grow"
                                @dragover.prevent="onColumnDragOver('favorites')"
                                @drop.prevent="(event) => onColumnDrop('favorites', 0, event)"
                            >
                                {{ t('pages.aiNews.favoritesEmpty') }}
                            </div>
                        </div>
                    </div>
                </el-col>
            </el-row>
        </el-card>
    </div>
</template>

<script setup lang="ts" name="demo-ai-news">
import { onMounted, ref } from 'vue';
import { useI18n } from 'vue-i18n';
import { Star } from '@element-plus/icons-vue';
import { ElMessage } from 'element-plus';
import {
    favoriteDevGuideKey,
    loadAiNewsBoard,
    type AiNewsColumnId,
    type ResolvedLink,
    useAiNewsBoard,
} from './ai-news-links-store';
import LinkCard from './ai-news-link-card.vue';

const { t } = useI18n();
const {
    internationalLinks,
    domesticLinks,
    favoriteLinks,
    pinToTop,
    moveItem,
    removeFromBoard,
    addFavorite,
    removeFavorite,
    isFavorite,
    addCustomByUrl,
} = useAiNewsBoard();

const urlInput = ref('');
const prefsLoading = ref(true);
const dragOverColumn = ref<AiNewsColumnId | null>(null);
const dragInsertIndex = ref<number | null>(null);

const columnLength = (column: AiNewsColumnId) => {
    if (column === 'international') return internationalLinks.value.length;
    if (column === 'domestic') return domesticLinks.value.length;
    return favoriteLinks.value.length;
};

const resolveInsertIndex = (column: AiNewsColumnId, index: number, event: DragEvent) => {
    const el = event.currentTarget as HTMLElement | null;
    if (!el) return index;
    const rect = el.getBoundingClientRect();
    const insertAfter = event.clientY - rect.top > rect.height / 2;
    return insertAfter ? index + 1 : index;
};

const setDragInsert = (column: AiNewsColumnId, index: number) => {
    dragOverColumn.value = column;
    dragInsertIndex.value = index;
};

onMounted(async () => {
    try {
        await loadAiNewsBoard();
    } finally {
        prefsLoading.value = false;
    }
});

const displayDescForFavorites = (item: ResolvedLink) => {
    const guideKey = favoriteDevGuideKey(item);
    if (guideKey) {
        const msg = t(`pages.aiNews.devGuides.${guideKey}`);
        if (msg && msg !== `pages.aiNews.devGuides.${guideKey}`) return msg;
    }
    return item.description || item.url;
};

const openLink = (url: string) => {
    window.open(url, '_blank', 'noopener,noreferrer');
};

const parseDragPayload = (event: DragEvent) => {
    const raw = event.dataTransfer?.getData('application/x-ai-news-link');
    if (!raw) return null;
    try {
        return JSON.parse(raw) as { key: string; column: AiNewsColumnId; index: number };
    } catch {
        return null;
    }
};

const onColumnDragOver = (column: AiNewsColumnId) => {
    setDragInsert(column, columnLength(column));
};

const onColumnDragLeave = (column: AiNewsColumnId) => {
    if (dragOverColumn.value === column) {
        dragOverColumn.value = null;
        dragInsertIndex.value = null;
    }
};

const onItemDragOver = (column: AiNewsColumnId, index: number, event: DragEvent) => {
    setDragInsert(column, resolveInsertIndex(column, index, event));
};

const clearDragState = () => {
    dragOverColumn.value = null;
    dragInsertIndex.value = null;
};

const isInsertBefore = (column: AiNewsColumnId, index: number) =>
    dragOverColumn.value === column && dragInsertIndex.value === index;

const isInsertAfter = (column: AiNewsColumnId, index: number) =>
    dragOverColumn.value === column && dragInsertIndex.value === index + 1;

const onColumnDrop = (toColumn: AiNewsColumnId, toIndex: number, event: DragEvent) => {
    const payload = parseDragPayload(event);
    const insertAt = dragInsertIndex.value ?? toIndex;
    clearDragState();
    if (!payload) return;
    if (payload.column === toColumn && (insertAt === payload.index || insertAt === payload.index + 1)) {
        return;
    }
    moveItem(payload.key, payload.column, toColumn, insertAt);
};

const onPinTop = (column: AiNewsColumnId, item: ResolvedLink) => {
    pinToTop(column, item.key);
    ElMessage.success(t('pages.aiNews.pinned'));
};

const onAddUrl = async () => {
    const result = await addCustomByUrl(urlInput.value);
    if (result === 'invalid') {
        ElMessage.error(t('pages.aiNews.invalidUrl'));
        return;
    }
    if (result === 'duplicate') {
        ElMessage.warning(t('pages.aiNews.duplicateUrl'));
        return;
    }
    urlInput.value = '';
    ElMessage.success(t('pages.aiNews.added'));
};

const onDeleteLink = (item: ResolvedLink) => {
    removeFromBoard(item.key);
    ElMessage.success(t('pages.aiNews.removed'));
};

const onRemoveFavorite = (item: ResolvedLink) => {
    removeFavorite(item.key);
    ElMessage.success(t('pages.aiNews.unfavorited'));
};

const isFavoriteItem = (item: ResolvedLink) => isFavorite(item.key);

const onToggleFavorite = (item: ResolvedLink) => {
    if (isFavorite(item.key)) {
        removeFavorite(item.key);
        ElMessage.success(t('pages.aiNews.unfavorited'));
        return;
    }
    if (addFavorite(item.key)) {
        ElMessage.success(t('pages.aiNews.favorited'));
    }
};
</script>

<style scoped>
.ai-news-page {
    width: 100%;
}

.page-header {
    display: flex;
    align-items: center;
    justify-content: space-between;
}

.page-title {
    font-size: 18px;
    font-weight: 600;
}

.page-intro {
    margin: 0 0 12px;
    font-size: 14px;
    color: #666;
    line-height: 1.6;
}

.drag-hint {
    margin: 0 0 16px;
    font-size: 12px;
    color: #909399;
}

.add-bar {
    display: flex;
    gap: 12px;
    margin-bottom: 12px;
}

.add-bar .el-input {
    flex: 1;
}

.columns-row {
    align-items: stretch;
}

.columns-row :deep(.el-col) {
    display: flex;
}

.panel-box {
    flex: 1;
    display: flex;
    flex-direction: column;
    padding: 16px;
    border: 1px solid #ebeef5;
    border-radius: 10px;
    background: #fff;
    min-height: 100%;
    transition: border-color 0.2s, box-shadow 0.2s;
}

.panel-box--drop {
    border-color: #409eff;
    box-shadow: 0 0 0 2px rgba(64, 158, 255, 0.12);
}

.link-section {
    height: 100%;
}

.section-label {
    display: flex;
    align-items: center;
    gap: 6px;
    margin-bottom: 12px;
    font-size: 15px;
    font-weight: 600;
    color: #303133;
    flex-shrink: 0;
}

.fav-icon {
    color: #e6a23c;
}

.link-list {
    display: flex;
    flex-direction: column;
    gap: 12px;
}

.link-list--grow {
    flex: 1;
}

.link-item-wrapper {
    width: 100%;
    position: relative;
}

.link-item-wrapper--insert-before::before,
.link-item-wrapper--insert-after::after {
    content: '';
    position: absolute;
    left: 0;
    right: 0;
    height: 2px;
    background: #409eff;
    border-radius: 1px;
    pointer-events: none;
    z-index: 1;
}

.link-item-wrapper--insert-before::before {
    top: -7px;
}

.link-item-wrapper--insert-after::after {
    bottom: -7px;
}

.empty-hint {
    padding: 16px;
    font-size: 13px;
    color: #a8abb2;
    text-align: center;
    border: 1px dashed #dcdfe6;
    border-radius: 8px;
}

.favorites-panel {
    background: #fafcff;
}

.fav-hint {
    margin: 0 0 12px;
    font-size: 12px;
    color: #909399;
    line-height: 1.5;
    flex-shrink: 0;
}

.fav-empty {
    padding: 24px 12px;
    text-align: center;
    font-size: 13px;
    color: #a8abb2;
    border: 1px dashed #dcdfe6;
    border-radius: 8px;
}

.fav-empty--grow {
    flex: 1;
    display: flex;
    align-items: center;
    justify-content: center;
    min-height: 120px;
}

@media (max-width: 992px) {
    .columns-row .el-col + .el-col {
        margin-top: 20px;
    }
}
</style>
