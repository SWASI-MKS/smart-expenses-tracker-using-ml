from django.shortcuts import render, redirect, HttpResponseRedirect
from .forms import User_Profile, UserProfileForm
from django.contrib import messages
from django.contrib.auth.models import User
from userincome.models import Source
from .models import UserProfile


def userprofile(request):
    """
    User profile view that handles:
    - Displaying user profile information
    - Updating user details (first_name, last_name, email)
    - Uploading profile image with validation
    - Managing income sources
    """
    # Get user's income sources
    sources = Source.objects.filter(owner=request.user)
    
    if request.user.is_authenticated:
        # Get or create user profile
        user_profile, created = UserProfile.objects.get_or_create(user=request.user)
        
        if request.method == "POST":
            # Handle user fields update
            user_form = User_Profile(data=request.POST, instance=request.user)
            
            # Handle profile image upload
            profile_image = request.FILES.get('profile_image')
            
            if profile_image:
                # Validate file type
                allowed_types = ['image/jpeg', 'image/jpg', 'image/png', 'image/webp']
                if profile_image.content_type not in allowed_types:
                    messages.error(request, 'Invalid file type. Please upload a JPG, PNG, or WebP image.')
                    return render(request, 'userprofile/profile.html', {
                        'user_form': user_form,
                        'sources': sources,
                        'profile': user_profile
                    })
                
                # Validate file size (max 2MB)
                if profile_image.size > 2 * 1024 * 1024:
                    messages.error(request, 'File too large. Maximum size is 2MB.')
                    return render(request, 'userprofile/profile.html', {
                        'user_form': user_form,
                        'sources': sources,
                        'profile': user_profile
                    })
                
                # Delete old image if exists
                if user_profile.profile_image:
                    try:
                        user_profile.profile_image.delete(save=False)
                    except Exception:
                        pass
                
                # Save new image
                user_profile.profile_image = profile_image
                user_profile.save()
                messages.success(request, 'Profile image updated successfully!')
            
            # Save user information
            if user_form.is_valid():
                user_form.save()
                messages.success(request, 'Profile Updated Successfully!')
            else:
                # Handle form errors
                for field, errors in user_form.errors.items():
                    for error in errors:
                        messages.error(request, f'{field}: {error}')
            
            # Redirect to prevent form resubmission
            return redirect('account')
        else:
            user_form = User_Profile(instance=request.user)
        
        return render(request, 'userprofile/profile.html', {
            'user_form': user_form,
            'sources': sources,
            'profile': user_profile
        })
    else:
        messages.info(request, "You need to login first to view your profile")
        return HttpResponseRedirect('/authentication/login/')


def addSource(request):
    """
    Add a new income source for the user.
    """
    if request.method == "POST":
        newSource = request.POST.get('Source', '').strip()
        
        if not newSource:
            messages.error(request, "Source name cannot be empty")
            return redirect('account')
        
        if Source.objects.filter(name=newSource, owner=request.user).exists():
            messages.warning(request, "Income source already exists")
            return redirect('account')
        
        # Create new source
        newsourceadded = Source.objects.create(name=newSource, owner=request.user)
        newsourceadded.save()

        messages.success(request, 'Source added successfully')
        return redirect('account')
    
    # If not POST, redirect to account page
    return redirect('account')


def deleteSource(request, id):
    """
    Delete an income source for the user.
    """
    try:
        source = Source.objects.get(pk=id, owner=request.user)
        source.delete()
        messages.success(request, "Source deleted successfully")
    except Source.DoesNotExist:
        messages.error(request, "Source not found")
    
    return redirect('account')

