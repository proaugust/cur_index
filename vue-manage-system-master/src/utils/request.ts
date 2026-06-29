import axios, { AxiosInstance, AxiosError, AxiosResponse, InternalAxiosRequestConfig } from 'axios';

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
