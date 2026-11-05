import axios, { AxiosInstance, AxiosError, AxiosResponse, InternalAxiosRequestConfig } from 'axios';

function currentInnerTab(): string {
    const content = document.querySelector('.content');
    if (!content) return '';
    const items = content.querySelectorAll('.el-tabs__item.is-active');
    for (const item of items) {
        const el = item as HTMLElement;
        if (el.offsetParent === null && el.getClientRects().length === 0) continue;
        const text = (el.textContent || '').replace(/\s+/g, ' ').trim();
        if (text) return text.slice(0, 100);
    }
    return '';
}

const service: AxiosInstance = axios.create({
    baseURL: '/api',
    timeout: 120000,
});

service.interceptors.request.use(
    (config: InternalAxiosRequestConfig) => {
        const token = localStorage.getItem('access_token');
        if (token) {
            config.headers.Authorization = `Bearer ${token}`;
        }
        const page = window.location.hash.replace(/^#/, '').split('?')[0];
        if (page.startsWith('/')) {
            config.headers['X-Page'] = page.slice(0, 200);
        }
        const tab = currentInnerTab();
        if (tab) {
            config.headers['X-Tab'] = encodeURIComponent(tab);
        }
        return config;
    },
    (error: AxiosError) => {
        console.log(error);
        return Promise.reject();
    }
);

service.interceptors.response.use(
    (response: AxiosResponse) => {
        if (response.status === 200) {
            return response;
        } else {
            Promise.reject();
        }
    },
    (error: AxiosError) => {
        if (error.response?.status === 401) {
            localStorage.removeItem('access_token');
            localStorage.removeItem('vuems_name');
            localStorage.removeItem('vuems_permissions');
            if (!window.location.hash.includes('/login')) {
                window.location.hash = '#/login';
            }
        }
        return Promise.reject(error);
    }
);

export default service;
