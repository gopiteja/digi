-- phpMyAdmin SQL Dump
-- version 4.8.0.1
-- https://www.phpmyadmin.net/
--
-- Host: localhost
-- Generation Time: Feb 23, 2019 at 11:02 AM
-- Server version: 10.1.32-MariaDB
-- PHP Version: 7.0.30

SET SQL_MODE = "NO_AUTO_VALUE_ON_ZERO";
SET AUTOCOMMIT = 0;
START TRANSACTION;
SET time_zone = "+00:00";


/*!40101 SET @OLD_CHARACTER_SET_CLIENT=@@CHARACTER_SET_CLIENT */;
/*!40101 SET @OLD_CHARACTER_SET_RESULTS=@@CHARACTER_SET_RESULTS */;
/*!40101 SET @OLD_COLLATION_CONNECTION=@@COLLATION_CONNECTION */;
/*!40101 SET NAMES utf8mb4 */;

--
-- Database: `wns_files`
--
CREATE database wns_files;
USE wns_files;

-- --------------------------------------------------------

--
-- Table structure for table `files_info`
--

CREATE TABLE `files_info` (
  `id` int(11) NOT NULL,
  `file_name` varchar(100) NOT NULL,
  `case_id` varchar(64) DEFAULT NULL,
  `ocr_data` text DEFAULT NULL,
  `user_id` int(11) DEFAULT NULL,
  `status` boolean DEFAULT NULL,
  `created_date` datetime(1) DEFAULT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8;

--
-- Dumping data for table `files_info`
--

INSERT INTO `files_info` (`id`, `file_name`, `case_id`, `ocr_data`, `user_id`, `status`, `created_date`) VALUES
(1, 'x.jpg', '123', 'OCR data', 1, '0', '0000-00-00 00:00:00.0'),
(2, 'y.jpg', '456', 'Long OCR data', 1, '1', '0000-00-00 00:00:00.0'),
(3, 'z.jpg', '678', 'Short OCR data', 1, '1', '0000-00-00 00:00:00.0'),
(4, 'x.jpg', '123', 'Medium OCR data', 1, '1', '0000-00-00 00:00:00.0');

--
-- Indexes for dumped tables
--

--
-- Indexes for table `files_info`
--
ALTER TABLE `files_info`
  ADD PRIMARY KEY (`id`);

--
-- AUTO_INCREMENT for dumped tables
--

--
-- AUTO_INCREMENT for table `files_info`
--
ALTER TABLE `files_info`
  MODIFY `id` int(11) NOT NULL AUTO_INCREMENT, AUTO_INCREMENT=5;
COMMIT;

/*!40101 SET CHARACTER_SET_CLIENT=@OLD_CHARACTER_SET_CLIENT */;
/*!40101 SET CHARACTER_SET_RESULTS=@OLD_CHARACTER_SET_RESULTS */;
/*!40101 SET COLLATION_CONNECTION=@OLD_COLLATION_CONNECTION */;
