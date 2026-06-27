<template>
    <div class="header">
        <!-- 折叠按钮 -->
        <div class="header-left">
            <img class="logo" src="../assets/img/logo.svg" alt="" />
            <div class="web-title">{{ t('header.appTitle') }}</div>
            <div class="collapse-btn" @click="collapseChage">
                <el-icon v-if="sidebar.collapse">
                    <Expand />
                </el-icon>
                <el-icon v-else>
                    <Fold />
                </el-icon>
            </div>
        </div>
        <div class="header-right">
            <div class="header-user-con">
                <el-dropdown class="lang-switch" trigger="click" @command="setLocale">
                    <span class="lang-link">
                        {{ localeStore.locale === 'zh-CN' ? t('header.langZh') : t('header.langJa') }}
                        <el-icon class="el-icon--right"><arrow-down /></el-icon>
                    </span>
                    <template #dropdown>
                        <el-dropdown-menu>
                            <el-dropdown-item command="zh-CN">中文</el-dropdown-item>
                            <el-dropdown-item command="ja-JP">日本語</el-dropdown-item>
                        </el-dropdown-menu>
                    </template>
                </el-dropdown>
                <div class="btn-icon" @click="router.push('/theme')">
                    <el-tooltip effect="dark" :content="t('header.theme')" placement="bottom">
                        <i class="el-icon-lx-skin"></i>
                    </el-tooltip>
                </div>
                <div class="btn-icon" @click="router.push('/ucenter')">
                    <el-tooltip
                        effect="dark"
                        :content="message ? t('header.unreadMessages', { count: message }) : t('header.messageCenter')"
                        placement="bottom"
                    >
                        <i class="el-icon-lx-notice"></i>
                    </el-tooltip>
                    <span class="btn-bell-badge" v-if="message"></span>
                </div>
                <div class="btn-icon" @click="setFullScreen">
                    <el-tooltip effect="dark" :content="t('header.fullscreen')" placement="bottom">
                        <i class="el-icon-lx-full"></i>
                    </el-tooltip>
                </div>
                <!-- 用户头像 -->
                <el-avatar class="user-avator" :size="30" :src="imgurl" />
                <!-- 用户名下拉菜单 -->
                <el-dropdown class="user-name" trigger="click" @command="handleCommand">
                    <span class="el-dropdown-link">
                        {{ username }}
                        <el-icon class="el-icon--right">
                            <arrow-down />
                        </el-icon>
                    </span>
                    <template #dropdown>
                        <el-dropdown-menu>
                            <el-dropdown-item command="user">{{ t('header.userCenter') }}</el-dropdown-item>
                            <el-dropdown-item divided command="loginout">{{ t('header.logout') }}</el-dropdown-item>
                        </el-dropdown-menu>
                    </template>
                </el-dropdown>
            </div>
        </div>
    </div>
</template>
<script setup lang="ts">
import { onMounted } from 'vue';
import { useI18n } from 'vue-i18n';
import { useSidebarStore } from '../store/sidebar';
import { useLocaleStore } from '../store/locale';
import { useRouter } from 'vue-router';
import type { AppLocale } from '@/i18n';
import imgurl from '../assets/img/img.jpg';

const { t } = useI18n();
const localeStore = useLocaleStore();

const username: string | null = localStorage.getItem('vuems_name');
const message: number = 2;

const sidebar = useSidebarStore();
const collapseChage = () => {
    sidebar.handleCollapse();
};

const setLocale = (command: string) => {
    localeStore.setLocale(command as AppLocale);
};

onMounted(() => {
    if (document.body.clientWidth < 1500) {
        collapseChage();
    }
});

const router = useRouter();
const handleCommand = (command: string) => {
    if (command == 'loginout') {
        localStorage.removeItem('vuems_name');
        router.push('/login');
    } else if (command == 'user') {
        router.push('/ucenter');
    }
};

const setFullScreen = () => {
    if (document.fullscreenElement) {
        document.exitFullscreen();
    } else {
        document.body.requestFullscreen.call(document.body);
    }
};
</script>
<style scoped>
.header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    box-sizing: border-box;
    width: 100%;
    height: 70px;
    color: var(--header-text-color);
    background-color: var(--header-bg-color);
    border-bottom: 1px solid #ddd;
}

.header-left {
    display: flex;
    align-items: center;
    padding-left: 20px;
    height: 100%;
}

.logo {
    width: 35px;
}

.web-title {
    margin: 0 40px 0 10px;
    font-size: 22px;
}

.collapse-btn {
    display: flex;
    justify-content: center;
    align-items: center;
    height: 100%;
    padding: 0 10px;
    cursor: pointer;
    opacity: 0.8;
    font-size: 22px;
}

.collapse-btn:hover {
    opacity: 1;
}

.header-right {
    float: right;
    padding-right: 50px;
}

.header-user-con {
    display: flex;
    height: 70px;
    align-items: center;
}

.btn-fullscreen {
    transform: rotate(45deg);
    margin-right: 5px;
    font-size: 24px;
}

.btn-icon {
    position: relative;
    width: 30px;
    height: 30px;
    text-align: center;
    cursor: pointer;
    display: flex;
    align-items: center;
    color: var(--header-text-color);
    margin: 0 5px;
    font-size: 20px;
}

.lang-switch {
    margin-right: 8px;
    cursor: pointer;
}

.lang-link {
    display: inline-flex;
    align-items: center;
    color: var(--header-text-color);
    font-size: 14px;
    white-space: nowrap;
}

.btn-bell-badge {
    position: absolute;
    right: 4px;
    top: 0px;
    width: 8px;
    height: 8px;
    border-radius: 4px;
    background: #f56c6c;
    color: var(--header-text-color);
}

.user-avator {
    margin: 0 10px 0 20px;
}

.el-dropdown-link {
    color: var(--header-text-color);
    cursor: pointer;
    display: flex;
    align-items: center;
}

.el-dropdown-menu__item {
    text-align: center;
}
</style>
