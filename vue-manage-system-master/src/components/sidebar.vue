<template>
    <div class="sidebar">
        <el-menu
            class="sidebar-el-menu"
            :default-active="onRoutes"
            :collapse="sidebar.collapse"
            :background-color="sidebar.bgColor"
            :text-color="sidebar.textColor"
            router
        >
            <template v-for="item in visibleMenu" :key="item.index">
                <template v-if="item.children">
                    <el-sub-menu :index="item.index">
                        <template #title>
                            <el-icon>
                                <component :is="item.icon"></component>
                            </el-icon>
                            <span>{{ menuTitle(item) }}</span>
                        </template>
                        <template v-for="subItem in item.children" :key="subItem.index">
                            <el-sub-menu v-if="subItem.children" :index="subItem.index">
                                <template #title>{{ menuTitle(subItem) }}</template>
                                <el-menu-item
                                    v-for="(threeItem, i) in subItem.children"
                                    :key="i"
                                    :index="threeItem.index"
                                >
                                    {{ menuTitle(threeItem) }}
                                </el-menu-item>
                            </el-sub-menu>
                            <el-menu-item v-else :index="subItem.index">
                                {{ menuTitle(subItem) }}
                            </el-menu-item>
                        </template>
                    </el-sub-menu>
                </template>
                <template v-else>
                    <el-menu-item :index="item.index">
                        <el-icon>
                            <component :is="item.icon"></component>
                        </el-icon>
                        <template #title>{{ menuTitle(item) }}</template>
                    </el-menu-item>
                </template>
            </template>
        </el-menu>
    </div>
</template>

<script setup lang="ts">
import { computed } from 'vue';
import { useI18n } from 'vue-i18n';
import { useSidebarStore } from '../store/sidebar';
import { usePermissStore } from '../store/permiss';
import { useRoute } from 'vue-router';
import { menuData } from '@/components/menu';
import { filterMenuByPermiss } from '@/utils/menu';
import type { Menus } from '@/types/menu';

const { t } = useI18n();
const permiss = usePermissStore();

const menuTitle = (item: Menus) => {
    if (item.titleKey === '403' || item.titleKey === '404') return item.titleKey;
    return t(item.titleKey);
};

const visibleMenu = computed(() => filterMenuByPermiss(menuData, permiss.menuKeys));

const route = useRoute();
const onRoutes = computed(() => route.path);

const sidebar = useSidebarStore();
</script>

<style scoped>
.sidebar {
    display: block;
    position: absolute;
    left: 0;
    top: 70px;
    bottom: 0;
    overflow-y: scroll;
}

.sidebar::-webkit-scrollbar {
    width: 0;
}

.sidebar-el-menu:not(.el-menu--collapse) {
    width: 250px;
}
</style>
