import { Menus } from '@/types/menu';

export const menuData: Menus[] = [
    {
        id: '0',
        title: '系统首页',
        index: '/dashboard',
        icon: 'Odometer',
    },
    {
        id: '1',
        title: '系统管理',
        index: '1',
        icon: 'HomeFilled',
        children: [
            {
                id: '11',
                pid: '1',
                index: '/system-user',
                title: '用户管理',
            },
            {
                id: '12',
                pid: '1',
                index: '/system-role',
                title: '角色管理',
            },
            {
                id: '13',
                pid: '1',
                index: '/system-menu',
                title: '菜单管理',
            },
        ],
    },
    {
        id: '8',
        title: '业务展示',
        index: '8',
        icon: 'DataAnalysis',
        children: [
            {
                id: '81',
                pid: '8',
                index: '/demo-complaints',
                title: '投诉归类',
            },
            {
                id: '82',
                pid: '8',
                index: '/demo-rag',
                title: 'RAG 检索',
            },
            {
                id: '83',
                pid: '8',
                index: '/demo-ai-chat',
                title: 'AI训练提问',
            },
            {
                id: '84',
                pid: '8',
                index: '/demo-agent',
                title: 'Agent 展示',
            },
            {
                id: '85',
                pid: '8',
                index: '/demo-meeting',
                title: '会议整理',
            },
            {
                id: '86',
                pid: '8',
                index: '/demo-smart-route',
                title: '智能路由',
            },
            {
                id: '87',
                pid: '8',
                index: '/demo-attendance',
                title: '人脸打卡',
            },
        ],
    },
    {
        id: '7',
        icon: 'Brush',
        index: '/theme',
        title: '主题',
    },
    {
        id: '6',
        icon: 'DocumentAdd',
        index: '6',
        title: '附加页面',
        children: [
            {
                id: '61',
                pid: '6',
                index: '/ucenter',
                title: '个人中心',
            },
            {
                id: '62',
                pid: '6',
                index: '/login',
                title: '登录',
            },
            {
                id: '63',
                pid: '6',
                index: '/register',
                title: '注册',
            },
            {
                id: '64',
                pid: '6',
                index: '/reset-pwd',
                title: '重设密码',
            },
            {
                id: '65',
                pid: '6',
                index: '/403',
                title: '403',
            },
            {
                id: '66',
                pid: '6',
                index: '/404',
                title: '404',
            },
        ],
    },
];
