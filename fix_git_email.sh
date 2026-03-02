#!/bin/bash

echo "=========================================="
echo "  Fix Git Email Privacy Issue"
echo "=========================================="
echo ""

echo "GitHub is blocking your push because of email privacy settings."
echo ""
echo "You have 2 options:"
echo ""
echo "Option 1: Use GitHub's no-reply email (Recommended)"
echo "  - Keeps your email private"
echo "  - Format: USERNAME@users.noreply.github.com"
echo ""
echo "Option 2: Disable email privacy on GitHub"
echo "  - Go to: https://github.com/settings/emails"
echo "  - Uncheck 'Keep my email addresses private'"
echo ""

read -p "Choose option (1 or 2): " option

if [ "$option" = "1" ]; then
    echo ""
    echo "Your GitHub username appears to be: ajha63"
    read -p "Is this correct? (Y/n): " correct
    
    if [[ ! $correct =~ ^[Nn]$ ]]; then
        username="ajha63"
    else
        read -p "Enter your GitHub username: " username
    fi
    
    # Check if you have a GitHub ID-based email
    echo ""
    echo "GitHub provides two types of no-reply emails:"
    echo "  1. USERNAME@users.noreply.github.com"
    echo "  2. ID+USERNAME@users.noreply.github.com (more private)"
    echo ""
    echo "To find your ID-based email:"
    echo "  1. Go to: https://github.com/settings/emails"
    echo "  2. Look for an email like: 12345678+username@users.noreply.github.com"
    echo ""
    
    read -p "Do you want to use the ID-based email? (y/N): " use_id
    
    if [[ $use_id =~ ^[Yy]$ ]]; then
        read -p "Enter your full GitHub no-reply email: " email
    else
        email="${username}@users.noreply.github.com"
    fi
    
    echo ""
    echo "Setting Git email to: $email"
    git config user.email "$email"
    
    echo "Amending the last commit with new email..."
    git commit --amend --reset-author --no-edit
    
    echo ""
    echo "✓ Email updated successfully!"
    echo ""
    echo "Now try pushing again:"
    echo "  git push -u origin main"
    
elif [ "$option" = "2" ]; then
    echo ""
    echo "To disable email privacy:"
    echo "  1. Go to: https://github.com/settings/emails"
    echo "  2. Uncheck 'Keep my email addresses private'"
    echo "  3. Uncheck 'Block command line pushes that expose my email'"
    echo "  4. Then try pushing again: git push -u origin main"
    echo ""
else
    echo "Invalid option"
    exit 1
fi
