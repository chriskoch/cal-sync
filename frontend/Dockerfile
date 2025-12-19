# Development Dockerfile for frontend
FROM node:20-alpine

WORKDIR /app

# Copy package files
COPY package*.json ./

# Install dependencies
RUN npm install

# Copy source code
COPY . .

# Expose Vite dev server port
EXPOSE 3033

# Run Vite dev server
CMD ["npm", "run", "dev"]
