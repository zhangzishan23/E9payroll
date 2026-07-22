FROM node:18-alpine AS build

WORKDIR /app

RUN npm config set registry https://registry.npmmirror.com

COPY package*.json ./
RUN npm ci

COPY . .

ARG VITE_ROUTE_PREFIX=/e9salary
ENV VITE_ROUTE_PREFIX=${VITE_ROUTE_PREFIX}

RUN npm run build

FROM nginx:alpine

COPY --from=build /app/dist /usr/share/nginx/html/e9salary
COPY nginx.conf /etc/nginx/conf.d/default.conf

EXPOSE 8080

CMD ["nginx", "-g", "daemon off;"]
