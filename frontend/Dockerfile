FROM node:22-alpine

WORKDIR /app

# Copy dependency specifications
COPY package*.json ./

# Install dependencies
RUN npm install

# Copy application source
COPY . .

# Expose Vite dev server port
EXPOSE 5173

# Run Vite with host binding for Docker
CMD ["npm", "run", "dev", "--", "--host", "0.0.0.0", "--port", "5173"]
