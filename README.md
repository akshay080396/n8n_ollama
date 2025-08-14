# MCP_MONGODB_ORDER_ANALYTICS

A completely independent MongoDB-powered order analytics dashboard with Streamlit, featuring natural language query processing using Llama 3 and interactive data visualization for e-commerce order data.

## 🚀 Features

- **🔄 Fully Containerized**: Complete Docker setup with no local dependencies
- **🍃 Integrated MongoDB**: Containerized MongoDB with automatic sample data loading
- **🤖 AI-Powered Queries**: Natural language processing using Llama 3
- **📊 Interactive Visualizations**: Dynamic charts with Plotly (Bar, Line, Pie charts)
- **🔗 MCP Server Support**: Model Context Protocol for MongoDB operations
- **📈 Order Analytics**: Analyze order status, payment data, delivery costs, and customer locations
- **💾 Persistent Storage**: All data saved in Docker volumes

## 📋 Prerequisites

- **Docker Desktop** installed and running
- **Docker Compose** (included with Docker Desktop)
- **No local MongoDB or Ollama required!**

## 🎯 Quick Start (Complete Independence)

### **Option 1: One-Click Setup (Windows)**
```bash
# Simply run the startup script
start_independent_system.bat
```

### **Option 2: Manual Setup**
```bash
# Start the complete system
docker-compose up -d

# Access the dashboard
# http://localhost:8501
```

## 🏗️ System Architecture

The system includes these containerized services:

- **🍃 MongoDB** (port 27017): Database with pre-loaded sample order data
- **🤖 Ollama** (port 11434): AI service with Llama 3 model (reuses existing volume)
- **📊 Streamlit App** (port 8501): Interactive analytics dashboard
- **🔗 MCP Server** (port 3000): MongoDB Model Context Protocol server

## 📊 Sample Data Structure

The system comes pre-loaded with sample `ordercollections` containing:
- `orderId`: Unique order identifier
- `status`: Order status (DELIVERED, NEW, PICKUP_EXCEPTION, etc.)
- `paymentStatus`: Payment status (SUCCESS, PENDING)
- `orderDetails.totalPrice`: Order total amount
- `orderDetails.orderChannel`: Sales channel (Instagram, Facebook, Website, etc.)
- `buyerDetails.permanentAddress.city/country`: Customer location
- `createdAt`: Order creation date
- Complete order lifecycle data

## 🤖 Example AI Queries

Try these natural language questions:
- "Show the total number of orders by status"
- "What is the total revenue by payment status"
- "Which cities have the most orders"
- "Show Instagram orders only"
- "List all delivered orders"
- "What is the average order value by country"
- "Show the top 5 orders by total price"
- "What's the revenue trend by order channel"

## 🔧 Configuration

### Docker Compose Services
```yaml
services:
  mongodb:       # Containerized MongoDB with sample data
  ollama:        # AI service (reuses existing models)
  streamlit-app: # Analytics dashboard
  mongodb-mcp-server: # MCP protocol server
```

### Volume Management
- `mongodb_data`: Persistent MongoDB storage
- `ollama_data`: Reuses existing `ai_dashboard_ollama_data` volume
- No data loss between restarts

## 🔍 Troubleshooting

### System Won't Start
```bash
# Check Docker is running
docker info

# Check service logs
docker-compose logs -f

# Restart clean
docker-compose down
docker-compose up -d
```

### AI Features Not Working
```bash
# Check Ollama status
docker exec ollama ollama list

# If no models, install Llama 3
docker exec ollama ollama pull llama3
```

### No Sample Data
```bash
# Reinitialize MongoDB data
docker-compose down
docker volume rm mcp_postgres_automated_mongodb_data
docker-compose up -d
```

## 🎮 System Controls

### Start System
```bash
# Windows
start_independent_system.bat

# Manual
docker-compose up -d
```

### Stop System
```bash
docker-compose down
```

### View Logs
```bash
docker-compose logs -f
```

### Access Services
- **📈 Analytics Dashboard**: http://localhost:8501
- **🍃 MongoDB**: mongodb://localhost:27017/admin
- **🤖 Ollama API**: http://localhost:11434
- **🔗 MCP Server**: http://localhost:3000

## 🌟 Advantages of This Setup

- ✅ **Zero Local Dependencies**: No need to install MongoDB or Ollama locally
- ✅ **Instant Setup**: One command starts the entire system
- ✅ **Consistent Environment**: Works the same on any system with Docker
- ✅ **Sample Data Included**: Ready to test immediately
- ✅ **Persistent Storage**: Data survives container restarts
- ✅ **Model Reuse**: Leverages existing Ollama models to avoid re-downloading
- ✅ **Complete Isolation**: Won't interfere with local installations
- ✅ **Easy Cleanup**: Simple to remove completely when done

## 🧹 Cleanup

To completely remove the system:
```bash
# Stop and remove containers
docker-compose down

# Remove volumes (optional - loses data)
docker volume rm mcp_postgres_automated_mongodb_data

# Remove images (optional)
docker image rm mongo:latest mongodb/mongodb-mcp-server:latest
```

This setup provides a completely independent, portable MongoDB analytics system that works consistently across different environments! 🎉