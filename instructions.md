for my personal view that sorts for overdue invoices, i use the following filters:
Type: is customer invoice,
Status: is pending,
Due date: is or is before today

Now this may be the gui representation of an API request, i dont know how closely the terms match up. It gives me a list of all the overdue invoices. I also have the option of viewing anything about the document, like the account, job location name, the document ID, and "Job: Location: ID"

example curl request to test your grant:

curl https://api.jobtread.com/pave -d '{
  "query": {
    "$": { "grantKey": "22TJC5HGU5NYLJNsG42PzsxeNAn8ptsMLV" },
    "currentGrant": { "id": {} }
  }
}'

-----


Overall goal: write a script that downloads PDF's of overdue invoices. The PDF's are downloaded into folders by account/location.

Currently, I have a custom view in the frontend that shows me all overdue invoices. I have to click each one, and request a PDF. Requesting a PDF for 

document ID: 22PD5FmpBe4D,
job: location ID: 22NzTqB2t2Vu

opens the link https://app.jobtread.com/redirect/https://cdn.jobtread.com/G0EACBWh0hVal_ry4eHOptAgwQYcB8oDDjQQXgpIrZr15EUCC82YbNtA0Ir0uSQFca6f6mAXZTDUH06pqMgSFdmUFfgB.mSL2ev-aoc7950rl90BsQBCNT7jX0HM0ZYw3fjSGXDs?download

I am wondering if requesting document PDF's is supported by the API. Lets start there. Then we can work on requesting a list of document ID's and such.