<template>
    <div
        class="link-item"
        role="link"
        tabindex="0"
        @click="emit('open', item.url)"
        @keydown.enter="emit('open', item.url)"
        @keydown.space.prevent="emit('open', item.url)"
    >
        <el-button
            class="fav-btn"
            link
            :title="favorited ? favoritedTitle : favoriteTitle"
            @click.stop="emit('favorite', item)"
        >
            <el-icon :class="{ 'fav-btn__icon--active': favorited }">
                <StarFilled v-if="favorited" />
                <Star v-else />
            </el-icon>
        </el-button>
        <div
            v-if="iconFailed"
            class="site-icon site-icon--letter"
            :style="{ background: item.color, color: letterColor(item.color) }"
        >
            {{ item.letter }}
        </div>
        <img
            v-else
            class="site-icon"
            :src="item.icon"
            :alt="name"
            loading="lazy"
            @error="emit('icon-error', item.key)"
        />
        <div class="link-info">
            <div class="link-name">{{ name }}</div>
            <div class="link-desc">{{ desc }}</div>
            <div class="link-url">{{ item.url }}</div>
        </div>
        <span class="open-hint">
            {{ openLabel }}
            <el-icon class="open-icon"><TopRight /></el-icon>
        </span>
        <el-button
            class="delete-btn"
            type="danger"
            link
            :title="deleteTitle"
            @click.stop="emit('delete', item)"
        >
            <el-icon><Delete /></el-icon>
        </el-button>
    </div>
</template>

<script setup lang="ts">
import { computed } from 'vue';
import { useI18n } from 'vue-i18n';
import { Delete, Star, StarFilled, TopRight } from '@element-plus/icons-vue';
import type { ResolvedLink } from './ai-news-links-store';

defineProps<{
    item: ResolvedLink;
    name: string;
    desc: string;
    iconFailed: boolean;
    favorited: boolean;
}>();

const emit = defineEmits<{
    open: [url: string];
    'icon-error': [key: string];
    delete: [item: ResolvedLink];
    favorite: [item: ResolvedLink];
}>();

const { t } = useI18n();

const favoriteTitle = computed(() => t('pages.aiNews.clickToFavorite'));
const favoritedTitle = computed(() => t('pages.aiNews.removeFavorite'));
const deleteTitle = computed(() => t('pages.aiNews.delete'));
const openLabel = computed(() => t('pages.aiNews.open'));

const letterColor = (bg: string) => {
    const hex = bg.replace('#', '');
    if (hex.length !== 6) return '#fff';
    const r = parseInt(hex.slice(0, 2), 16);
    const g = parseInt(hex.slice(2, 4), 16);
    const b = parseInt(hex.slice(4, 6), 16);
    const luminance = (0.299 * r + 0.587 * g + 0.114 * b) / 255;
    return luminance > 0.62 ? '#303133' : '#ffffff';
};
</script>

<style scoped>
.link-item {
    display: flex;
    align-items: flex-start;
    gap: 10px;
    padding: 14px 12px 14px 10px;
    border: 1px solid #ebeef5;
    border-radius: 8px;
    cursor: pointer;
    transition: border-color 0.2s, box-shadow 0.2s, background-color 0.2s;
}

.link-item:hover {
    border-color: #c6e2ff;
    background-color: #f5f9ff;
    box-shadow: 0 2px 8px rgba(64, 158, 255, 0.08);
}

.link-item:focus-visible {
    outline: 2px solid #409eff;
    outline-offset: 2px;
}

.fav-btn {
    flex-shrink: 0;
    width: 28px;
    height: 32px;
    padding: 0;
    margin: 0;
    color: #c0c4cc;
}

.fav-btn:hover {
    color: #e6a23c;
}

.fav-btn__icon--active {
    color: #e6a23c;
}

.site-icon {
    flex-shrink: 0;
    width: 32px;
    height: 32px;
    border-radius: 6px;
    object-fit: contain;
    background: #f5f7fa;
    padding: 2px;
}

.site-icon--letter {
    display: flex;
    align-items: center;
    justify-content: center;
    font-size: 13px;
    font-weight: 700;
    padding: 0;
    line-height: 1;
}

.link-info {
    flex: 1;
    min-width: 0;
}

.link-name {
    font-size: 15px;
    font-weight: 600;
    color: #303133;
    margin-bottom: 4px;
}

.link-desc {
    font-size: 13px;
    color: #909399;
    margin-bottom: 6px;
    line-height: 1.5;
}

.link-url {
    font-size: 12px;
    color: #a8abb2;
    word-break: break-all;
}

.open-hint {
    flex-shrink: 0;
    display: inline-flex;
    align-items: center;
    margin-top: 2px;
    font-size: 14px;
    color: #409eff;
}

.open-icon {
    margin-left: 2px;
}

.delete-btn {
    flex-shrink: 0;
    margin-top: 2px;
}
</style>
