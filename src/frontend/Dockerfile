FROM nginx:alpine

# Copy file cấu hình Nginx Reverse Proxy
COPY nginx.conf /etc/nginx/conf.d/default.conf

# Copy toàn bộ file tĩnh (HTML, CSS, JS) vào thư mục web
COPY . /usr/share/nginx/html

EXPOSE 80

CMD ["nginx", "-g", "daemon off;"]
