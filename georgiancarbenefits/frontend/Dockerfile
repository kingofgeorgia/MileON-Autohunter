FROM node:20-alpine AS base

WORKDIR /app
COPY package*.json ./
RUN npm ci --legacy-peer-deps && \
    npm install --no-save @parcel/watcher-linux-x64-musl

COPY . .
ENV NEXT_TELEMETRY_DISABLED=1

CMD ["npm", "run", "dev"]
