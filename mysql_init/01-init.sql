-- MySQL initialization script for Notu
-- This script is automatically executed when the MySQL container starts

-- Create database if it doesn't exist
CREATE DATABASE IF NOT EXISTS `notu` CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;

-- Create user if it doesn't exist
CREATE USER IF NOT EXISTS 'notu'@'%' IDENTIFIED BY 'notu123';

-- Grant all privileges on the notu database to the notu user
GRANT ALL PRIVILEGES ON `notu`.* TO 'notu'@'%';

-- Flush privileges to ensure changes take effect
FLUSH PRIVILEGES;

-- Use the notu database
USE `notu`;

-- Create a simple test table to verify the setup
CREATE TABLE IF NOT EXISTS `database_setup_test` (
    `id` INT AUTO_INCREMENT PRIMARY KEY,
    `message` VARCHAR(255) NOT NULL,
    `created_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Insert a test record
INSERT INTO `database_setup_test` (`message`) VALUES ('Notu database setup completed successfully!');
