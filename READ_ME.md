# Web Content Manager User Guide

Welcome to the **Web Content Manager**, a tool to save, organize, and manage web links efficiently. This guide explains how to use the application for **Admin**, **Guest**, and **Public** users. Follow the step-by-step instructions to log in, add links, browse, search, delete, export, and (for Admins) view analytics.

## Table of Contents
- [Overview](#overview)
- [Getting Started: Login](#getting-started-login)
  - [Admin Login](#admin-login)
  - [Guest Login](#guest-login)
  - [Public Login](#public-login)
- [Using the Application](#using-the-application)
  - [Switching Between Mobile and Desktop Views](#switching-between-mobile-and-desktop-views)
  - [Adding a Single Link](#adding-a-single-link)
  - [Uploading Browser Bookmarks](#uploading-browser-bookmarks)
  - [Browsing and Searching Links](#browsing-and-searching-links)
  - [Deleting Links](#deleting-links)
  - [Exporting Links](#exporting-links)
  - [Viewing Analytics (Admin Only)](#viewing-analytics-admin-only)
  - [Debug Tools](#debug-tools)
- [Tips and Notes](#tips-and-notes)

## Overview
The Web Content Manager helps you:
- 📌 Save web links with titles, descriptions, tags, and priorities.
- 🏷️ Automatically suggest tags from web page metadata.
- 🔍 Search links by keywords, tags, or priority.
- 🗑️ Delete unwanted links.
- 📊 View links in a sortable table.
- 📥 Export links as Excel or CSV files.
- 💾 Save data persistently (Admin/Guest) or temporarily (Public).
- 📱 Toggle between mobile (~360px wide) and desktop (~90% viewport) layouts.

The app has three user modes:
- **Admin**: Full access, including analytics.
- **Guest**: Save links to a personal file, no analytics.
- **Public**: Temporary storage, links lost on logout unless exported.

## Getting Started: Login
The app starts at the login screen. Choose your user type and follow the steps below.

### Admin Login
1. On the login screen, select **Admin** from the “Select Login Type” radio buttons.
2. In the form, enter the Admin password: `******`.
3. Click **Login**.
4. If successful, you’ll see “✅ Logged in as Admin!” with balloons, and the app loads with tabs: **Add Link**, **Browse Links**, **Export Data**, and **Analytics**.

### Guest Login
1. Select **Guest** from the radio buttons.
2. Enter a **Username** (e.g., “kru”) and the Guest password: `******`.
3. Click **Login**.
4. If successful, you’ll see “✅ Logged in as Guest (kru)!” with balloons, and the app loads with tabs: **Add Link**, **Browse Links**, and **Export Data**.
5. Your links are saved to a file named `links_<username>.xlsx` (e.g., `links_kru.xlsx`).

### Public Login
1. Select **Public** from the radio buttons.
2. Click **👥 Continue as Public User**.
3. You’ll see “✅ Continuing as Public User!” with balloons, and the app loads with tabs: **Add Link**, **Browse Links**, and **Export Data**.
4. **Important**: Public user links are temporary and will be lost when you log out. Use **Export Data** to save your links.

## Using the Application
After logging in, you’ll see the app header with:
- **Web Content Manager** title and description.
- **Mode** (e.g., “Guest Mode (kru)”).
- **🚪 Logout** button (left).
- **📱/📺 Toggle** button (right) to switch layouts.
- **Tabs** for navigation (Add Link, Browse Links, etc.).

### Switching Between Mobile and Desktop Views
The app supports two layouts:
- **Mobile View**: Narrow (~360px), ideal for phones, with stacked inputs and compact tables.
- **Desktop View**: Wide (~90% of screen), ideal for larger screens, with side-by-side inputs and wider tables.

To toggle:
1. Locate the toggle button next to the “Logout” button:
   - 📱 (mobile icon) means you’re in desktop view; click to switch to mobile.
   - 📺 (desktop icon) means you’re in mobile view; click to switch to desktop.
2. Click the icon. The app will refresh, and the layout will change:
   - **Mobile View**: Content is centered, ~360px wide; search inputs stack vertically; table columns are narrower (e.g., URL column ~100px).
   - **Desktop View**: Content spans ~90% of the screen; search inputs align horizontally; table columns are wider (e.g., URL column ~200px).
3. Check the debug text below the toggle: “Debug: Current layout mode=mobile” or “desktop” to confirm the mode.

### Adding a Single Link
Use the **Add Link** tab to save a single web link.
1. Go to the **Add Link** tab and select the **Single URL** sub-tab.
2. Enter a URL (e.g., `https://www.example.com`) in the “URL*” field. Ensure it starts with `http://` or `https://`.
3. Click **Fetch Metadata** (enabled only for valid URLs). The app will:
   - Fill the “Title*” and “Description” fields with data from the webpage.
   - Suggest tags in the “Tags” dropdown (or show “⚠️ No tags found...”).
4. In the form below:
   - Confirm the **URL**.
   - Edit the **Title** if needed.
   - Add or edit the **Description**.
   - Select **Tags** from the dropdown (populated with existing tags, defaults like “News,” and suggested tags). Add a new tag in the “Add New Tag” field if desired.
   - Choose a **Priority** (Low, Medium, High, Important).
   - Set a **Number** (for grouping, default 0).
5. Click **💾 Save Link**.
6. If successful, you’ll see “✅ Link saved successfully!” with balloons. If the URL is a duplicate, a warning appears: “⚠️ This URL is a duplicate.”
7. The form clears, and the link is added to your collection.

### Uploading Browser Bookmarks
Use the **Add Link** tab to import multiple links from a file.
1. Go to the **Add Link** tab and select the **Upload Bookmarks** sub-tab.
2. Click **Choose file** to upload an Excel (`.xlsx`), CSV (`.csv`), or HTML (`.html`) bookmark file.
3. Select how to handle duplicates: **Keep Both** or **Skip Duplicates**.
4. Click **Import Bookmarks**.
5. A progress bar shows the import status. When complete, you’ll see “✅ Bookmarks imported! X new links added.” If duplicates are detected, a warning appears.
6. The imported links are added to your collection.

### Browsing and Searching Links
Use the **Browse Links** tab to view, search, and filter your links.
1. Go to the **Browse Links** tab. If you have links, a table displays with columns: **URL** (clickable), **Title**, **Description**, **Tags**, **Priority**, **Number**, **Is Duplicate**, and **Delete** (checkbox).
2. Use the search and filter options above the table:
   - **Search Links**: Enter keywords to search titles, descriptions, URLs, or tags.
   - **Filter by Tags**: Select tags from the dropdown to show links with those tags.
   - **Filter by Priority**: Choose a priority (e.g., High) or “All” to show all links.
3. Click **🔍 Search Web** to open a Google search with your query and tags in a new tab.
4. The table updates to show matching links, sorted by priority (Important > High > Medium > Low) and number.
5. If no links match, you’ll see “No links match the search criteria.”
6. In mobile view, columns are narrower; in desktop view, they’re wider.

### Deleting Links
You can delete links from the **Browse Links** tab.
1. In the table, check the **Delete** box for each link you want to remove.
2. A **🗑️ Delete Selected Links** button appears once at least one box is checked.
3. Click **Delete Selected Links**.
4. If successful, you’ll see “✅ Selected links deleted successfully!” with a snow animation, and the links are removed.
5. For Admin/Guest, deletions are saved to Google Drive. For Public, they’re removed from temporary storage.

### Exporting Links
Use the **Export Data** tab to download your links.
1. Go to the **Export Data** tab.
2. If you have links, a **Download Links as Excel** button appears.
3. Click the button to download an Excel file (`links.xlsx`) with columns: sequence number, link ID, URL (clickable), title, description, tags, priority, number, created_at, updated_at, is_duplicate.
4. For Public users, this is critical to save your links before logging out, as they’re temporary.

### Viewing Analytics (Admin Only)
Admins can view analytics in the **Analytics** tab.
1. Log in as Admin and go to the **Analytics** tab.
2. View three charts:
   - **Most Frequent URLs**: Bar chart of the top 5 URLs.
   - **Most Common Tags**: Bar chart of tag frequencies.
   - **User Activity Trends**: Line chart of links added per day.
3. If no data exists, you’ll see “No data available for analytics.”

### Debug Tools
The **Add Link** tab includes a “Debug Tools” expander for troubleshooting.
1. In the **Add Link** tab, under **Single URL**, expand **Debug Tools**.
2. Use the buttons:
   - **Show Session State Keys**: Lists non-sensitive session state keys.
   - **Show Tag Info**: Displays suggested tags, auto-title, and auto-description from metadata.
   - **Clear Non-Critical Session State**: Resets temporary data (e.g., form inputs) without affecting links or login. You’ll see “✅ Non-critical session state cleared.”
3. These tools are safe and won’t cause errors like the previous debug button issue.

## Tips and Notes
- **Public Users**: Always export your links before logging out to avoid data loss.
- **Mobile View**: Use the 📱 toggle for a phone-like experience, especially on smaller screens.
- **Tags**: Add new tags in the “Add New Tag” field to organize links better.
- **Duplicates**: Check the “Is Duplicate” column to identify repeated URLs.
- **Google Drive**: Admin/Guest links are saved to Google Drive automatically. Ensure your Google Drive secrets are configured.
- **Logout**: Click **🚪 Logout** to return to the login screen. Your data is safe (except for Public users).
- **Need Help?**: Check this guide or contact support via the repository’s issues page.

Happy link managing! 🚀
