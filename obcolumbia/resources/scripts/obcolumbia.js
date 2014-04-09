$(document).on("click", "a.main_btn",  function(e) {
	e.preventDefault();								
	var thisDiv = "#"+$(this).attr("id").replace("_btn", "_dropdown");
	$(thisDiv).addClass("active");
});
$(document).on("click", ".menu_dropdown a.close",  function(e) {
	e.preventDefault();
	var thisContainer = $(this).parents("div");
	
	$(thisContainer).removeClass("active");
});
$(document).on("click", "a#post",  function(e) {
	e.preventDefault();
	$("div#post_dropdown").addClass("active");
});
$(document).on("click", "a#sharelink",  function(e) {
	e.preventDefault();
	$(this).toggleClass("active");
	$("div#theLink").toggleClass("active");
});
$(document).on("click", "#theLink", function() {
	// Select input field contents
	$(this).selectText();
});
jQuery.fn.selectText = function(){
   var doc = document;
   var element = this[0];
   console.log(this, element);
   if (doc.body.createTextRange) {
	   var range = document.body.createTextRange();
	   range.moveToElementText(element);
	   range.select();
   } else if (window.getSelection) {
	   var selection = window.getSelection();        
	   var range = document.createRange();
	   range.selectNodeContents(element);
	   selection.removeAllRanges();
	   selection.addRange(range);
   }
};
$(document).on("click", "a#list_button", function(e) {
	e.preventDefault();
	$(this).toggleClass("active");
	if ($(this).hasClass("active")) {
		$("#headline_wrapper").show("slide", { direction: "left" }, 250); 
	} else {
		$("#headline_wrapper").hide("slide", { direction: "left" }, 250); 
	}
	closeEmbed()
});

$("form#map_center").live("submit", function(e){
		e.preventDefault();
		 $("div.olControlLoadingPanel").show();
		var addressToGeocode = $(this).find("input").val().trim();
        if (addressToGeocode == '') {
            alert("Please enter an address");
            return;
        }
        $j.ajax({url: '/api/dev1/geocode/',
                type: 'GET',
                data: {'q': addressToGeocode},
                dataType: 'json',
                success: handleGeocoderResult, 
                error: handleNoGeocoderResult
        });	
	});
  
  
	var handleNoGeocoderResult = function(xhr, status, err) {
        if (xhr.status == 404) {
          alert('No results found, please try a different address');
		   $("div.olControlLoadingPanel").hide();
        }
        else {
          alert('An error occurred looking up this location.');
		  $("div.olControlLoadingPanel").hide();
        }
      };
      
      var handleGeocoderResult = function(data, status, req) {
        var MapLink = $(".olControlPermalink a").attr("href")
		var center = $.urlParam("c", MapLink); 
		if ($("#iframe_area").is(":visible")) {
			MapLink = MapLink+"&embed=true";
		}
		
		for (var i = 0 ; i < data.features.length; i++) {
          var result = data.features[i]; 
          var result_title = "";
            
			
			MapLink = (MapLink.replace(center,result.geometry.coordinates[0]+"_"+result.geometry.coordinates[1]))+"&point=true&z=17&address="+$("form#map_center").find("input").val().trim();
			
			
			window.location = MapLink;
		   
        }

        if (data.features.length > 0) {
          selectResult($j('.geocoder-result').get(0));
        }
        else {
          selectNone();
        }
      };
		

	$.urlParam = function(name, passedLocation){
			passedLocation = passedLocation || location.search;
			return decodeURIComponent((new RegExp('[?|&]' + name + '=' + '([^&;]+?)(&|#|;|$)').exec(passedLocation)||[,""])[1].replace(/\+/g, '%20'))||null
	}
	
$(document).on("click", "#bigmap a#post", function(e) {
		e.preventDefault();
		$("div#post").toggle("slide", { direction: "down" }, 250); 
		$("#permalink_popup").hide(); 
		$("#layerswitcher-container").removeClass("active", 250); 
		$("div.checkLabel:visible").hide();
});
$(document).on("click", "#bigmap div#post a.close", function(e) {
	e.preventDefault();
	$("div#post").toggle("slide", { direction: "down" }, 250); 
})
$(document).on("click", "a#permalink_btn", function(e) {
		e.preventDefault();
		var theLink = $(".olControlPermalink a").attr("href");
		var bounds = $.urlParam("bounds");
		var loc_url = $.urlParam("loc_url");
		var loc_title = $.urlParam("loc_title");
		var point = $.urlParam("point")
		if (bounds != null && loc_url != null && loc_title != null) {
			theLink = theLink+"&bounds="+bounds+"&loc_url="+loc_url+"&loc_title="+loc_title;
		}
		if (point != null) {
			theLink = theLink+"&point="+point;
		}
		$("#permalink_popup").toggle("slide", { direction: "down" }, 250); 
		$("#layerswitcher-container").removeClass("active", 250); 
		$("div#post").hide(); 
		$("#theLink").html(theLink);

		var newFacebook = $("a#facebook_button").attr("href")+theLink;
		$("a#facebook_button").attr("href", newFacebook);

		var newTwitter = $("a#twitter_button").attr("href")+theLink;
		$("a#twitter_button").attr("href", newTwitter)	
});
$(document).on("click", "#permalink_popup a.close", function(e) {
			e.preventDefault();
			$("#permalink_popup").toggle("slide", { direction: "down" }, 250); 
			var TinyUrl = $("#theLink").html();
			var newFacebook = "https://www.facebook.com/sharer/sharer.php?u="
			$("a#facebook_button").attr("href", newFacebook)
			
			var newTwitter = "http://twitter.com/share?text=Explore your neighborhood on Open Block&url=";
			$("a#twitter_button").attr("href", newTwitter)
			$("#theLink").html("Loading");
})	

$(document).on("click", "a#filters_toggle", function(e) {
	e.preventDefault();
	$('div.filter_options').toggle();
	$(this).find("span").toggle();
});
		