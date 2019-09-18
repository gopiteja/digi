-- phpMyAdmin SQL Dump
-- version 4.8.5
-- https://www.phpmyadmin.net/
--
-- Host: db
-- Generation Time: May 25, 2019 at 03:12 PM
-- Server version: 5.7.26
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
CREATE DATABASE IF NOT EXISTS `authentication` DEFAULT CHARACTER SET utf8 COLLATE utf8_general_ci;
USE `authentication`;

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
(3, 'uat_user_01', 'S723277274', 'closed', '2019-04-16 09:34:19', '2019-05-16 10:52:50'),
(4, 'uat_lead_01', 'S984661120', 'active', '2019-04-16 10:52:26', '2019-05-15 07:18:16'),
(5, 'uat_user_02', 'S444151838', 'closed', '2019-04-16 10:57:22', '2019-04-25 10:47:02'),
(6, 'P400000451', 'S745917381', 'active', '2019-04-18 15:58:52', '2019-04-18 15:59:13'),
(7, 'P40000451', 'S126700468', 'active', '2019-04-22 05:55:57', '2019-05-07 11:27:39'),
(8, 'P40000009', 'S507544724', 'active', '2019-04-22 11:44:16', '2019-05-24 06:01:52'),
(9, 'P40000188', 'S480814742', 'active', '2019-05-03 05:39:55', '2019-05-03 07:08:12'),
(10, 'P40000188', 'S480814742', 'active', '2019-05-03 05:39:55', '2019-05-03 07:08:12'),
(11, 'P40000696', 'S115205995', 'active', '2019-05-03 05:42:01', '2019-05-24 08:37:59'),
(12, 'P40000652', 'S132740660', 'active', '2019-05-03 05:42:41', '2019-05-24 09:13:31'),
(13, 'P40000635', 'S336289699', 'active', '2019-05-13 08:48:04', '2019-05-24 11:01:54'),
(14, 'testing_team_02', 'S473971762', 'active', '2019-05-16 10:50:01', '2019-05-16 10:50:24'),
(15, 'testing_team_01', 'S336463761', 'closed', '2019-05-16 10:56:40', '2019-05-23 12:27:31'),
(16, 'P90007910', 'S298292820', 'closed', '2019-05-24 12:09:11', '2019-05-24 14:00:37');

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
(1, 'uat_user_01', '03ac674216f3e15c761ee1a5e255f067953623c8b388b4459e13f978d7c846f4', 'ashyam.zubair@algonox.com', 'UAT User 01', 'PM_Prod', 1),
(2, 'uat_lead_01', '03ac674216f3e15c761ee1a5e255f067953623c8b388b4459e13f978d7c846f4', 'ashyam.zubair@algonox.com', 'UAT Lead 01', 'TL_Prod', 1),
(3, 'uat_user_02', '03ac674216f3e15c761ee1a5e255f067953623c8b388b4459e13f978d7c846f4', 'ashyam.zubair@algonox.com', 'UAT User 02', 'PM_Prod', 1),
(4, 'P40000451', '03ac674216f3e15c761ee1a5e255f067953623c8b388b4459e13f978d7c846f4', 'ashyam.zubair@algonox.com', 'Abhishek', 'Process Member', 1),
(5, 'P40000009', '03ac674216f3e15c761ee1a5e255f067953623c8b388b4459e13f978d7c846f4', 'ashyam.zubair@algonox.com', 'P40000009', 'TL_Prod', 1),
(6, 'P40000188', '03ac674216f3e15c761ee1a5e255f067953623c8b388b4459e13f978d7c846f4', 'ashyam.zubair@algonox.com', 'P40000188', 'PM_Prod', 1),
(7, 'P40000696', '03ac674216f3e15c761ee1a5e255f067953623c8b388b4459e13f978d7c846f4', 'ashyam.zubair@algonox.com', 'P40000696', 'PM_Prod', 1),
(8, 'P40000652', '03ac674216f3e15c761ee1a5e255f067953623c8b388b4459e13f978d7c846f4', 'ashyam.zubair@algonox.com', 'P40000652', 'PM_Prod', 1),
(9, 'P40000652', '03ac674216f3e15c761ee1a5e255f067953623c8b388b4459e13f978d7c846f4', 'ashyam.zubair@algonox.com', 'P40000652', 'PM_Prod', 1),
(10, 'P40000696', '03ac674216f3e15c761ee1a5e255f067953623c8b388b4459e13f978d7c846f4', 'ashyam.zubair@algonox.com', 'P40000696', 'PM_Prod', 1),
(11, 'P40000635', '03ac674216f3e15c761ee1a5e255f067953623c8b388b4459e13f978d7c846f4', 'ashyam.zubair@algonox.com', 'P40000635', 'PM_Prod', 1),
(12, 'testing_team_01', '03ac674216f3e15c761ee1a5e255f067953623c8b388b4459e13f978d7c846f4', 'ashyam.zubair@algonox.com', 'testing_team_01', 'PM_Prod', 1),
(13, 'testing_team_02', '03ac674216f3e15c761ee1a5e255f067953623c8b388b4459e13f978d7c846f4', 'ashyam.zubair@algonox.com', 'testing_team_02', 'PM_Prod', 1),
(14, 'P90007910', '03ac674216f3e15c761ee1a5e255f067953623c8b388b4459e13f978d7c846f4', 'ashyam.zubair@algonox.com', 'P90007910', 'TL_Prod', 1);

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
  MODIFY `id` int(255) NOT NULL AUTO_INCREMENT, AUTO_INCREMENT=17;

--
-- AUTO_INCREMENT for table `users`
--
ALTER TABLE `users`
  MODIFY `id` int(11) NOT NULL AUTO_INCREMENT, AUTO_INCREMENT=15;
COMMIT;

/*!40101 SET CHARACTER_SET_CLIENT=@OLD_CHARACTER_SET_CLIENT */;
/*!40101 SET CHARACTER_SET_RESULTS=@OLD_CHARACTER_SET_RESULTS */;
/*!40101 SET COLLATION_CONNECTION=@OLD_COLLATION_CONNECTION */;
