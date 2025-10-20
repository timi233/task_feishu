# task_feishu/frontend/Dockerfile

# 使用Nginx官方镜像作为基础镜像
FROM nginx:alpine

# 删除Nginx默认的配置和页面
# Nginx的默认网站根目录是 /usr/share/nginx/html
RUN rm -rf /usr/share/nginx/html/*

# 复制前端文件到Nginx的默认网站目录
COPY index.html /usr/share/nginx/html/

# （可选）复制自定义Nginx配置文件
# 如果你有自定义的nginx.conf，可以取消下面一行的注释
# COPY nginx.conf /etc/nginx/nginx.conf

# Nginx默认监听80端口
EXPOSE 80

# 启动Nginx
# 使用 "daemon off;" 参数让Nginx在前台运行，这样Docker容器才能持续运行
CMD ["nginx", "-g", "daemon off;"]