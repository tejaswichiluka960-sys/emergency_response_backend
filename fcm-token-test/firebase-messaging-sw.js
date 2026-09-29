importScripts('https://www.gstatic.com/firebasejs/10.14.1/firebase-app-compat.js');
importScripts('https://www.gstatic.com/firebasejs/10.14.1/firebase-messaging-compat.js');

firebase.initializeApp({
  apiKey: "AIzaSyAsCnC_y0PdtwIXo1zya_rhDMruG2qrJ1w",
  authDomain: "emergency-response-70b18.firebaseapp.com",
  projectId: "emergency-response-70b18",
  storageBucket: "emergency-response-70b18.firebasestorage.app",
  messagingSenderId: "186516221853",
  appId: "1:186516221853:web:28d5681478b15fb0ea4974"
});

firebase.messaging();
