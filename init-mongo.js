db = db.getSiblingDB('admin');

// Create the collection if it doesn't exist
db.createCollection('ordercollections');

// Sample order data
const sampleOrders = [
  {
    orderId: 1001,
    status: "DELIVERED",
    paymentStatus: "SUCCESS",
    userId: "user123",
    buyerDetails: {
      permanentAddress: {
        firstName: "John",
        lastName: "Doe",
        emailId: "john.doe@example.com",
        city: "New York",
        country: "USA",
        postalCode: "10001"
      }
    },
    orderDetails: {
      products: [
        {
          productName: "Laptop",
          sku: "LAP001",
          taxRate: 0.1,
          unitPrice: 999.99,
          quantity: 1
        }
      ],
      orderDate: new Date(),
      paymentMode: "Prepaid",
      orderChannel: "Website",
      totalPrice: 1099.99,
      totalWeight: 2.5
    },
    createdAt: new Date(),
    updatedAt: new Date()
  },
  {
    orderId: 1002,
    status: "DELIVERED",
    paymentStatus: "SUCCESS",
    userId: "user456",
    buyerDetails: {
      permanentAddress: {
        firstName: "Jane",
        lastName: "Smith",
        emailId: "jane.smith@example.com",
        city: "Los Angeles",
        country: "USA",
        postalCode: "90001"
      }
    },
    orderDetails: {
      products: [
        {
          productName: "Smartphone",
          sku: "PHN001",
          taxRate: 0.1,
          unitPrice: 699.99,
          quantity: 1
        }
      ],
      orderDate: new Date(),
      paymentMode: "Prepaid",
      orderChannel: "Instagram",
      totalPrice: 769.99,
      totalWeight: 0.5
    },
    createdAt: new Date(),
    updatedAt: new Date()
  },
  {
    orderId: 1003,
    status: "PENDING",
    paymentStatus: "PENDING",
    userId: "user789",
    buyerDetails: {
      permanentAddress: {
        firstName: "Bob",
        lastName: "Johnson",
        emailId: "bob.johnson@example.com",
        city: "Chicago",
        country: "USA",
        postalCode: "60601"
      }
    },
    orderDetails: {
      products: [
        {
          productName: "Headphones",
          sku: "AUD001",
          taxRate: 0.1,
          unitPrice: 199.99,
          quantity: 2
        }
      ],
      orderDate: new Date(),
      paymentMode: "COD",
      orderChannel: "Facebook",
      totalPrice: 439.98,
      totalWeight: 0.8
    },
    createdAt: new Date(),
    updatedAt: new Date()
  }
];

// Insert the sample data
db.ordercollections.insertMany(sampleOrders);

print("Sample data inserted successfully!"); 