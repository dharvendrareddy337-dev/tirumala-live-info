/*
 * Public browser configuration for Tirumala Live Info.
 * These are public client values, not secrets. Never put a Supabase service-role
 * key or Firebase service-account JSON in this file.
 */

self.TLI_CONFIG = {

  // Supabase configuration
  supabaseUrl: "https://aeongraajtbsfjpxvxlj.supabase.co",
  supabaseAnonKey: "sb_publishable_lg_20AMv1Vy2FCA_TMI0pA_bhuOje4T",

  // Firebase configuration
  firebase: {
    apiKey: "AIzaSyAX5mp7CfFMDXZtPIbV_3qPA8s3EFK_qik",
    authDomain: "tirumala-live-info.firebaseapp.com",
    projectId: "tirumala-live-info",
    storageBucket: "tirumala-live-info.firebasestorage.app",
    messagingSenderId: "485853907421",
    appId: "1:485853907421:web:36fcb7e9ba723c6d484e34"
  },

  // Public VAPID key - 
  firebaseVapidKey: "BCn9bNGKZWf-1qX5KbUJsJCEIDMHvp8fHqYZmljNK2UCnVXyKg-DIV9707pipt4R33gxnjyWKDtWFFlJJqVy7iQ"

};
