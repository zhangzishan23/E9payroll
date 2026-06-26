# 构建阶段
FROM m.daocloud.io/docker.io/library/node:18-alpine AS build

WORKDIR /app

# 用淘宝镜像加速 npm
RUN npm config set registry https://registry.npmmirror.com

COPY package*.json ./
RUN npm ci

COPY . .
RUN npm run build

# 运行阶段
FROM m.daocloud.io/docker.io/library/nginx:alpine

COPY --from=build /app/dist /usr/share/nginx/html
COPY nginx.conf /etc/nginx/conf.d/default.conf

EXPOSE 80

CMD ["nginx", "-g", "daemon off;"]