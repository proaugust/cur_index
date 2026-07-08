<template>
    <div class="wrapper">
        <v-header />
        <v-sidebar />
        <div class="content-box" :class="{ 'content-collapse': sidebar.collapse }">
            <v-tabs></v-tabs>
            <div class="content">
                <router-view v-slot="{ Component, route: viewRoute }">
                    <transition name="move" mode="out-in">
                        <keep-alive :include="cachedTabNames">
                            <component :is="Component" :key="viewRoute.fullPath" />
                        </keep-alive>
                    </transition>
                </router-view>
            </div>
        </div>
    </div>
</template>
<script setup lang="ts">
import { computed, onMounted } from 'vue';
import { useSidebarStore } from '@/store/sidebar';
import { useTabsStore } from '@/store/tabs';
import { prefetchDemoRoutes } from '@/utils/prefetch-demo-routes';
import vHeader from '@/components/header.vue';
import vSidebar from '@/components/sidebar.vue';
import vTabs from '@/components/tabs.vue';

const sidebar = useSidebarStore();
const tabs = useTabsStore();
const cachedTabNames = computed(() => tabs.nameList.filter((name) => name !== 'demo-attendance'));

onMounted(() => {
    prefetchDemoRoutes();
});
</script>

<style>
.wrapper {
    height: 100vh;
    overflow: hidden;
}
.content-box {
    position: absolute;
    left: 250px;
    right: 0;
    top: 70px;
    bottom: 0;
    padding-bottom: 30px;
    -webkit-transition: left 0.3s ease-in-out;
    transition: left 0.3s ease-in-out;
    background: #eef0fc;
    overflow: hidden;
}

.content {
    width: auto;
    height: 100%;
    padding: 20px;
    overflow-y: scroll;
    box-sizing: border-box;
}

.content::-webkit-scrollbar {
    width: 0;
}

.content-collapse {
    left: 65px;
}
</style>
