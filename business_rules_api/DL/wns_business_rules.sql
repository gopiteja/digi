-- phpMyAdmin SQL Dump
-- version 4.8.5
-- https://www.phpmyadmin.net/
--
-- Host: localhost
-- Generation Time: Apr 17, 2019 at 01:41 PM
-- Server version: 10.1.38-MariaDB
-- PHP Version: 7.3.3

SET SQL_MODE = "NO_AUTO_VALUE_ON_ZERO";
SET AUTOCOMMIT = 0;
START TRANSACTION;
SET time_zone = "+00:00";


/*!40101 SET @OLD_CHARACTER_SET_CLIENT=@@CHARACTER_SET_CLIENT */;
/*!40101 SET @OLD_CHARACTER_SET_RESULTS=@@CHARACTER_SET_RESULTS */;
/*!40101 SET @OLD_COLLATION_CONNECTION=@@COLLATION_CONNECTION */;
/*!40101 SET NAMES utf8mb4 */;

--
-- Database: `wns_business_rules`
--
CREATE DATABASE IF NOT EXISTS `wns_business_rules` DEFAULT CHARACTER SET latin1 COLLATE latin1_swedish_ci;
USE `wns_business_rules`;

-- --------------------------------------------------------

--
-- Table structure for table `sequence_data`
--

CREATE TABLE `sequence_data` (
  `id` int(11) NOT NULL,
  `template_name` varchar(255) DEFAULT NULL,
  `ifelse` varchar(255) DEFAULT NULL,
  `func_name` varchar(255) DEFAULT NULL,
  `parameters` varchar(255) DEFAULT NULL,
  `operation` varchar(255) DEFAULT NULL,
  `nested` tinyint(1) DEFAULT NULL,
  `rule_name` varchar(255) NOT NULL,
  `group` varchar(255) NOT NULL,
  `type` varchar(255) NOT NULL,
  `rule_string` longtext NOT NULL
) ENGINE=InnoDB DEFAULT CHARSET=latin1;

--
-- Indexes for dumped tables
--

--
-- Indexes for table `sequence_data`
--
ALTER TABLE `sequence_data`
  ADD PRIMARY KEY (`id`);

--
-- AUTO_INCREMENT for dumped tables
--

--
-- AUTO_INCREMENT for table `sequence_data`
--
ALTER TABLE `sequence_data`
  MODIFY `id` int(11) NOT NULL AUTO_INCREMENT;
COMMIT;

/*!40101 SET CHARACTER_SET_CLIENT=@OLD_CHARACTER_SET_CLIENT */;
/*!40101 SET CHARACTER_SET_RESULTS=@OLD_CHARACTER_SET_RESULTS */;
/*!40101 SET COLLATION_CONNECTION=@OLD_COLLATION_CONNECTION */;
