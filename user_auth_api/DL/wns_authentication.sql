-- phpMyAdmin SQL Dump
-- version 4.8.5
-- https://www.phpmyadmin.net/
--
-- Host: db
-- Generation Time: Apr 16, 2019 at 11:38 AM
-- Server version: 5.7.25
-- PHP Version: 7.2.14

SET SQL_MODE = "NO_AUTO_VALUE_ON_ZERO";
SET AUTOCOMMIT = 0;
START TRANSACTION;
SET time_zone = "+00:00";


/*!40101 SET @OLD_CHARACTER_SET_CLIENT=@@CHARACTER_SET_CLIENT */;
/*!40101 SET @OLD_CHARACTER_SET_RESULTS=@@CHARACTER_SET_RESULTS */;
/*!40101 SET @OLD_COLLATION_CONNECTION=@@COLLATION_CONNECTION */;
/*!40101 SET NAMES utf8mb4 */;

--
-- Database: `authentication`
--
CREATE DATABASE IF NOT EXISTS `wns_authentication` DEFAULT CHARACTER SET utf8 COLLATE utf8_general_ci;
USE `wns_authentication`;

-- --------------------------------------------------------

--
-- Table structure for table `live_sessions`
--

CREATE TABLE `live_sessions` (
  `id` int(255) NOT NULL,
  `user` varchar(255) NOT NULL,
  `session_id` varchar(255) NOT NULL,
  `status` varchar(255) NOT NULL,
  `login` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `logout` timestamp NOT NULL DEFAULT '0000-00-00 00:00:00'
) ENGINE=InnoDB DEFAULT CHARSET=latin1;

--
-- Dumping data for table `live_sessions`
--

INSERT INTO `live_sessions` (`id`, `user`, `session_id`, `status`, `login`, `logout`) VALUES
(1, 'ashyam', 'S482376958', 'closed', '2019-03-15 09:39:12', '2019-03-15 09:40:08'),
(2, 'ashyam', 'S616540571', 'closed', '2019-03-15 09:40:42', '2019-04-16 09:33:16'),
(3, 'uat_user_01', 'S709296484', 'active', '2019-04-16 09:34:19', '2019-04-16 10:56:55'),
(4, 'uat_lead_01', 'S791755771', 'closed', '2019-04-16 10:52:26', '2019-04-16 10:56:43'),
(5, 'uat_user_02', 'S296701863', 'active', '2019-04-16 10:57:22', '2019-04-16 10:57:23');

-- --------------------------------------------------------

--
-- Table structure for table `users`
--

CREATE TABLE `users` (
  `id` int(11) NOT NULL,
  `username` varchar(50) NOT NULL,
  `password` varchar(64) NOT NULL,
  `email` varchar(100) NOT NULL,
  `name` varchar(100) NOT NULL,
  `role` varchar(50) NOT NULL,
  `status` tinyint(1) NOT NULL
) ENGINE=InnoDB DEFAULT CHARSET=latin1;

--
-- Dumping data for table `users`
--

INSERT INTO `users` (`id`, `username`, `password`, `email`, `name`, `role`, `status`) VALUES
(1, 'uat_user_01', '03ac674216f3e15c761ee1a5e255f067953623c8b388b4459e13f978d7c846f4', 'ashyam.zubair@algonox.com', 'UAT User 01', 'Process Member', 1),
(2, 'uat_lead_01', '03ac674216f3e15c761ee1a5e255f067953623c8b388b4459e13f978d7c846f4', 'ashyam.zubair@algonox.com', 'UAT Lead 01', 'Team Lead', 1),
(3, 'uat_user_02', '03ac674216f3e15c761ee1a5e255f067953623c8b388b4459e13f978d7c846f4', 'ashyam.zubair@algonox.com', 'UAT User 02', 'Process Member', 1);

--
-- Indexes for dumped tables
--

--
-- Indexes for table `live_sessions`
--
ALTER TABLE `live_sessions`
  ADD PRIMARY KEY (`id`);

--
-- Indexes for table `users`
--
ALTER TABLE `users`
  ADD PRIMARY KEY (`id`);

--
-- AUTO_INCREMENT for dumped tables
--

--
-- AUTO_INCREMENT for table `live_sessions`
--
ALTER TABLE `live_sessions`
  MODIFY `id` int(255) NOT NULL AUTO_INCREMENT, AUTO_INCREMENT=6;

--
-- AUTO_INCREMENT for table `users`
--
ALTER TABLE `users`
  MODIFY `id` int(11) NOT NULL AUTO_INCREMENT, AUTO_INCREMENT=4;
COMMIT;

/*!40101 SET CHARACTER_SET_CLIENT=@OLD_CHARACTER_SET_CLIENT */;
/*!40101 SET CHARACTER_SET_RESULTS=@OLD_CHARACTER_SET_RESULTS */;
/*!40101 SET COLLATION_CONNECTION=@OLD_COLLATION_CONNECTION */;
