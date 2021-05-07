const express = require('express');
const app = express();
const swaggerJsDoc = require('swagger-jsdoc');
const swaggerUI = require('swagger-ui-express');

const swaggerOptions = {
  swaggerDefinition: {
    info: {
      title: "Twitter Analysis API",
      version: '1.0.0',
    },
  },
  apis: ["app.js"],
};

const swaggerDocs = swaggerJsDoc(swaggerOptions);
app.use('/api-docs', swaggerUI.serve, swaggerUI.setup(swaggerDocs));

/**
 * @swagger
 * /tweets:
 *   get:
 *     description: Get all tweets
 *     responses:
 *       200:
 *         description: Success
 * 
 */
app.get('/tweets', (req, res) => {
  res.send([
    {
      id: 1,
      text: "Hello this is my tweet",
    }
  ])
});

/**
 * @swagger
 * /tweets:
 *   post:
 *     description: Create tweet
 *     parameters:
 *      - name: text
 *        description: text of the tweet
 *        in: formData
 *        required: true
 *        type: string
 *     responses:
 *       201:
 *         description: Created
 */
app.post('/tweets', (req, res) => {
  res.status(201).send();
});

app.listen(5000, () => console.log("listening on 5000"));
