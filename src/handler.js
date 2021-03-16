'use strict';
const AWS = require('aws-sdk');
const s3 = new AWS.S3({apiVersion: '2006-03-01'});
const simpleParser = require('mailparser').simpleParser;

const EMAIL_STAGING_BUCKET = `animl-email-staging-${process.env.STAGE}`;


module.exports.relayImages = async (event) => {
  const record = event.Records[0];
  const request = {
    Bucket: record.s3.bucket.name,
    Key: record.s3.object.key,
  };

  const filename = record.s3.object.key;
  console.log(`New object has been detected: ${filename}`);
  console.log('full event record: ', record);

  try {
    const data = await s3.getObject(request).promise();
    console.log('Raw email:' + data.Body);

    const email = await simpleParser(data.Body);

    console.log('date:', email.date);
    console.log('subject:', email.subject);
    console.log('body:', email.text);
    console.log('from:', email.from.text);
    console.log('attachments:', email.attachments);
    return { status: 'success' };
  }
  catch(Error) {
    console.log(Error, Error.stack);
    return Error;
  }

};
