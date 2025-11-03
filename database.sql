CREATE DATABASE IF NOT EXISTS wpb_bank;
USE wpb_bank;

-- Table for pending account opening requests
CREATE TABLE `account_requests` (
  `request_id` int NOT NULL AUTO_INCREMENT,
  `first_name` varchar(50) NOT NULL,
  `last_name` varchar(50) NOT NULL,
  `mobile_number` varchar(15) NOT NULL,
  `email` varchar(100) NOT NULL,
  `starting_deposit` decimal(15,2) NOT NULL,
  `password` varchar(255) NOT NULL,
  `status` varchar(20) DEFAULT 'pending',
  PRIMARY KEY (`request_id`)
);

-- Table for active customers
CREATE TABLE `customers` (
  `account_number` int NOT NULL,
  `first_name` varchar(50) NOT NULL,
  `last_name` varchar(50) NOT NULL,
  `mobile_number` varchar(15) NOT NULL,
  `email` varchar(100) NOT NULL,
  `password` varchar(255) NOT NULL,
  `balance` decimal(15,2) NOT NULL,
  PRIMARY KEY (`account_number`),
  UNIQUE KEY `email` (`email`)
);

-- Table for bank employees
CREATE TABLE `employees` (
  `id` int NOT NULL AUTO_INCREMENT,
  `name` varchar(100) NOT NULL,
  `email` varchar(100) NOT NULL,
  `password` varchar(255) NOT NULL,
  `requests_approved` int DEFAULT '0',
  `requests_denied` int DEFAULT '0',
  PRIMARY KEY (`id`),
  UNIQUE KEY `email` (`email`)
);

-- Inserting the two initial employees
INSERT INTO `employees` (`name`, `email`, `password`) VALUES
('Vedant Mankar', 'vman@gmail.com', '123'),
('Tanmay Kumar', 'tkumar@gmail.com', '1234');

-- Table for loan requests and active loans
CREATE TABLE `loans` (
  `loan_id` int NOT NULL AUTO_INCREMENT,
  `account_number` int NOT NULL,
  `amount` decimal(15,2) NOT NULL,
  `tenure` int NOT NULL,
  `interest_rate` float NOT NULL,
  `total_repayment` decimal(15,2) NOT NULL,
  `status` varchar(20) DEFAULT 'pending',
  PRIMARY KEY (`loan_id`),
  KEY `account_number` (`account_number`),
  CONSTRAINT `loans_ibfk_1` FOREIGN KEY (`account_number`) REFERENCES `customers` (`account_number`) ON DELETE CASCADE
);

ALTER TABLE loans
ADD COLUMN repayment_paid DECIMAL(15, 2) NOT NULL DEFAULT 0.00;