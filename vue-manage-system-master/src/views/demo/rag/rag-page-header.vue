<template>
    <div class="page-title-bar mgb20">
        <span class="page-title">{{ title }}</span>
    </div>
</template>

<script setup lang="ts" name="rag-page-header">
defineProps<{ title: string }>();
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
