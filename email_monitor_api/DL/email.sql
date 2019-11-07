-- phpMyAdmin SQL Dump
-- version 4.8.0.1
-- https://www.phpmyadmin.net/
--
-- Host: localhost
-- Generation Time: Mar 05, 2019 at 07:05 AM
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
-- Database: `email`
--
CREATE DATABASE IF NOT EXISTS `email` DEFAULT CHARACTER SET latin1 COLLATE latin1_swedish_ci;
USE `email`;

-- --------------------------------------------------------

--
-- Table structure for table `filtering_rules`
--
-- Creation: Feb 27, 2019 at 08:34 AM
--

CREATE TABLE `filtering_rules` (
  `id` int(11) NOT NULL,
  `related_id` varchar(100) NOT NULL,
  `attachment` tinyint(1) NOT NULL,
  `sender` varchar(100) NOT NULL,
  `cc` text NOT NULL,
  `subject_contains` text NOT NULL,
  `body_contains` text NOT NULL
) ENGINE=InnoDB DEFAULT CHARSET=latin1;

--
-- Dumping data for table `filtering_rules`
--

INSERT INTO `filtering_rules` (`id`, `related_id`, `attachment`, `sender`, `cc`, `subject_contains`, `body_contains`) VALUES
(1, 'prateek.dabas@algonox.com', 0, 'sender email', 'ashyam.zubair@algonox.com,ashish.khan@algonox.com', 'Subject keywords', 'Body keywords'),
(2, 'prateek.daba@algonox.com', 0, 'sender email', 'ashyam.zubair@algonox.com', 'Subject keywords 2', 'Body keywords 2');

-- --------------------------------------------------------

--
-- Table structure for table `user_email`
--
-- Creation: Mar 01, 2019 at 09:05 AM
--

CREATE TABLE `user_email` (
  `id` bigint(20) NOT NULL,
  `email` text,
  `folder` text,
  `server` text
) ENGINE=InnoDB DEFAULT CHARSET=latin1;

--
-- Dumping data for table `user_email`
--

INSERT INTO `user_email` (`id`, `email`, `folder`, `server`) VALUES
(0, 'prateek.daba@algonox.com', 'Inbox', 'imap.gmail.com'),
(1, 'prateek.dabas@algonox.com', 'Inbox', 'imap.gmail.com');

--
-- Indexes for dumped tables
--

--
-- Indexes for table `filtering_rules`
--
ALTER TABLE `filtering_rules`
  ADD PRIMARY KEY (`id`);

--
-- Indexes for table `user_email`
--
ALTER TABLE `user_email`
  ADD PRIMARY KEY (`id`),
  ADD KEY `ix_user_email_id` (`id`);

--
-- AUTO_INCREMENT for dumped tables
--

--
-- AUTO_INCREMENT for table `filtering_rules`
--
ALTER TABLE `filtering_rules`
  MODIFY `id` int(11) NOT NULL AUTO_INCREMENT, AUTO_INCREMENT=3;
COMMIT;

/*!40101 SET CHARACTER_SET_CLIENT=@OLD_CHARACTER_SET_CLIENT */;
/*!40101 SET CHARACTER_SET_RESULTS=@OLD_CHARACTER_SET_RESULTS */;
/*!40101 SET COLLATION_CONNECTION=@OLD_COLLATION_CONNECTION */;
